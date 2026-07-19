#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: ConnectomicDistance.py
Description:
    Region-level analogue of the physical-distance-from-seed analysis in
    AtlasGraphics.py. Instead of Euclidean voxel distance from a seed region
    (default: mPFC), the "distance" assigned to each region is the number of
    synaptic hops separating it from the seed, based on the Allen Mouse Brain
    Connectivity Atlas -- specifically the number of hops needed for that
    region to project INTO the seed (afferent/upstream direction). E.g. if a
    region projects directly into mPFC, it gets a connectomic distance of 1;
    if it only reaches mPFC via one intermediate region, it gets a
    connectomic distance of 2.

    Requires the `allensdk` and `networkx` packages to build the connectivity
    graph (`pip install allensdk networkx`). The structure-to-structure
    projection matrix is downloaded once via AllenSDK's MouseConnectivityCache
    and the resulting graph is cached to disk so repeated runs don't
    re-download or re-threshold the matrix.
Author: David Estrin
Date: 2026-07-19
Version: 1.0
"""
import os
import json
import pickle
import numpy as np
import pandas as pd
import networkx as nx
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import sem
import statsmodels.api as sm
from BrainBeam.registration.atlastree import atlastree

try:
    from allensdk.core.mouse_connectivity_cache import MouseConnectivityCache
    ALLENSDK_AVAILABLE = True
except ImportError:
    ALLENSDK_AVAILABLE = False


class AllenConnectivityGraph:
    """
    Directed graph of Allen Mouse Brain structure-to-structure anatomical
    connections. An edge from region A to region B means the Allen Mouse
    Connectivity Atlas found projection strength from A into B at or above
    `edge_threshold`; each edge therefore represents one monosynaptic hop.
    """

    def __init__(self, structure_ids, cache_dir, manifest_file=None,
                 projection_metric='normalized_projection_volume',
                 edge_threshold=0.01, hemisphere_id=3):
        if not ALLENSDK_AVAILABLE:
            raise ImportError(
                "allensdk is required for connectomic-distance analysis. "
                "Install it with `pip install allensdk`."
            )
        # `structure_ids=None` uses Allen's own curated "summary structure" set
        # (MouseConnectivityCache.default_structure_ids, ~316 structures). Tracer
        # experiments are almost never assigned a fine-grained structure (e.g. a
        # single cortical layer) as their primary injection site, so building the
        # graph over anything finer than this canonical set leaves most nodes with
        # zero in/out edges. Fine-grained regions get mapped up to their nearest
        # ancestor in this set at query time (see ConnectomicDistanceGraph).
        self.structure_ids = (
            None if structure_ids is None
            else list(dict.fromkeys(int(s) for s in structure_ids))
        )
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self.manifest_file = manifest_file or os.path.join(
            self.cache_dir, 'mouse_connectivity_manifest.json')
        self.projection_metric = projection_metric
        self.edge_threshold = edge_threshold
        self.hemisphere_id = hemisphere_id
        self.graph = None

    def build(self):
        """
        Fetch every Allen Mouse Connectivity Atlas tracer experiment injected into
        one of `structure_ids` (Allen's canonical summary structures if None), pull
        each experiment's projection strength into all of `structure_ids`, average
        per (source structure -> target structure) pair across experiments, and
        threshold the resulting structure x structure matrix into a directed graph
        (one edge = one monosynaptic hop).
        """
        mcc = MouseConnectivityCache(manifest_file=self.manifest_file)

        if self.structure_ids is None:
            self.structure_ids = list(dict.fromkeys(int(s) for s in mcc.default_structure_ids))

        experiments = mcc.get_experiments(cre=False, injection_structure_ids=self.structure_ids)
        if not experiments:
            raise ValueError(
                "No Allen Mouse Connectivity experiments found with injections in the "
                "given structures; cannot build a connectivity graph.")

        experiment_ids = [e['id'] for e in experiments]
        source_by_experiment = {e['id']: e['primary_injection_structure'] for e in experiments}

        matrix_info = mcc.get_projection_matrix(
            experiment_ids=experiment_ids,
            projection_structure_ids=self.structure_ids,
            hemisphere_ids=[self.hemisphere_id],
            parameter=self.projection_metric,
        )
        matrix = matrix_info['matrix']
        target_ids = [c['structure_id'] for c in matrix_info['columns']]

        # rows = experiments, columns = target structures
        proj_df = pd.DataFrame(matrix, index=experiment_ids, columns=target_ids)
        proj_df['__source_structure__'] = [source_by_experiment[eid] for eid in experiment_ids]

        # Average projection strength per source structure -> target structure,
        # ignoring experiments/targets with no measured value (NaN).
        source_target = proj_df.groupby('__source_structure__').mean()

        graph = nx.DiGraph()
        graph.add_nodes_from(self.structure_ids)
        for source_id, row in source_target.iterrows():
            for target_id, weight in row.items():
                if pd.isna(weight):
                    continue
                if source_id != target_id and weight >= self.edge_threshold:
                    graph.add_edge(int(source_id), int(target_id), weight=float(weight))

        self.graph = graph
        return graph

    def save(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as outfile:
            pickle.dump(self.graph, outfile)

    def load(self, path):
        with open(path, 'rb') as infile:
            self.graph = pickle.load(infile)
        return self.graph

    def hop_distance(self, region_id, seed_ids):
        """
        Minimum number of monosynaptic hops needed for `region_id` to reach
        ANY of `seed_ids` (e.g. the prelimbic/infralimbic/anterior-cingulate
        sub-structures that make up mPFC), following edge direction (an edge
        A->B means "A projects into B"). I.e. this answers "how many
        sequential projection hops does it take for `region_id` to project
        into the seed?" -- 1 if `region_id` directly projects into a seed
        structure, 2 if it projects into an intermediate region that directly
        projects into a seed structure, etc. Returns np.nan if no such
        directed path exists or `region_id` isn't part of the graph.
        """
        if self.graph is None:
            raise RuntimeError("Call build() (or load()) before computing hop distances.")

        seed_ids = [s for s in seed_ids if s in self.graph]
        if region_id not in self.graph or not seed_ids:
            return np.nan

        best = np.inf
        for seed_id in seed_ids:
            if region_id == seed_id:
                return 0
            try:
                length = nx.shortest_path_length(self.graph, source=region_id, target=seed_id)
                best = min(best, length)
            except nx.NetworkXNoPath:
                continue
        return best if np.isfinite(best) else np.nan


class ConnectomicDistanceGraph:
    """
    Computes, plots, and exports the relationship between a region's stat
    (default t_value) and its connectomic distance (# synaptic hops) from a
    seed region (default mPFC), using Allen Mouse Connectivity Atlas data.

    Mirrors the constructor/`__call__` pattern of AtlasGraphics.AtlasGraph so
    it can be dropped into the same pipeline alongside the physical-distance
    analyses.
    """

    def __init__(self, dataframe, atlas_path, drop_directory,
                 filename='connectomic_distance.jpg',
                 seed_regions=('prelimbic', 'infralimbic', 'anterior cingulate'),
                 projection_metric='normalized_projection_volume',
                 edge_threshold=0.01, connectivity_cache_dir=None,
                 graph_cache_path=None):
        self.df = dataframe.dropna(axis=0).copy()
        self.atlas_path = atlas_path
        self.drop_directory = drop_directory
        self.filename = filename
        self.abbreviated_filename = filename[:-4] if filename.lower().endswith(('.jpg', '.png')) else filename
        self.seed_regions = [s.lower() for s in seed_regions]
        self.projection_metric = projection_metric
        self.edge_threshold = edge_threshold
        self.connectivity_cache_dir = connectivity_cache_dir or os.path.join(
            self.atlas_path, 'allen_connectivity_cache')
        self.graph_cache_path = graph_cache_path or os.path.join(
            self.connectivity_cache_dir,
            f'connectivity_graph_{projection_metric}_{edge_threshold}.pkl')
        self.conn_graph = None

    def __call__(self, stat='t_value'):
        self.get_tree_obj()
        self.get_ids()
        self.build_connectivity_graph()
        self.compute_connection_distances()
        self.plot_tvalue_vs_connection_distance(stat=stat)
        self.plot_binned_tvalue_by_hops(stat=stat)

        out_csv = os.path.join(self.drop_directory, f'{self.abbreviated_filename}_connection_distances.csv')
        self.df.to_csv(out_csv, index=False)
        return self.df

    def get_tree_obj(self):
        drop_atlas_path = os.path.join(self.atlas_path, "communal_atlas_drop/")
        atlas_json_file = os.path.join(drop_atlas_path, 'structures.json')
        with open(atlas_json_file, 'r') as infile:
            ontology_dict = json.load(infile)
        ontology_dict_oh = {i: v for i, v in enumerate(ontology_dict)}
        self.tree_obj = atlastree(data=ontology_dict_oh)

    def get_ids(self):
        if 'id' in self.df.columns:
            return
        ids = []
        for name in self.df['regionname']:
            try:
                ids.append(self.tree_obj.find_node(id_or_name=name)['id'])
            except Exception as exc:
                raise ValueError(f'Unable to resolve atlas region ID for "{name}"') from exc
        self.df.insert(0, 'id', ids)

    def _seed_ids(self):
        is_seed = self.df['regionname'].str.lower().apply(
            lambda name: any(seed in name for seed in self.seed_regions)
        )
        return self.df[is_seed]['id'].values.tolist()

    def build_connectivity_graph(self):
        # Build over Allen's canonical ~316 summary structures (structure_ids=None),
        # not our atlas's fine-grained region ids. Tracer injections are almost
        # never assigned a single cortical layer (etc.) as their primary injection
        # site, so a graph built directly over fine-grained ids ends up with most
        # nodes (including the mPFC seed sub-regions) having zero edges. Fine
        # regions are instead mapped up to their nearest ancestor in this canonical
        # set at query time (see _resolve_to_graph_id / compute_connection_distances).
        self.conn_graph = AllenConnectivityGraph(
            structure_ids=None,
            cache_dir=self.connectivity_cache_dir,
            projection_metric=self.projection_metric,
            edge_threshold=self.edge_threshold,
        )
        if os.path.exists(self.graph_cache_path):
            self.conn_graph.load(self.graph_cache_path)
        else:
            self.conn_graph.build()
            self.conn_graph.save(self.graph_cache_path)

    def _resolve_to_graph_id(self, region_id):
        """
        Map `region_id` to the nearest ancestor (inclusive) present in the
        connectivity graph's node set, by walking up the atlas ontology tree.
        Returns None if no such ancestor exists.
        """
        valid_ids = self.conn_graph.graph
        if region_id in valid_ids:
            return region_id

        node = self.tree_obj.id_to_node.get(region_id)
        while node is not None:
            parent_id = node['parent']
            if parent_id is None:
                return None
            if parent_id in valid_ids:
                return parent_id
            node = self.tree_obj.id_to_node.get(parent_id)
        return None

    def compute_connection_distances(self):
        seed_ids = self._seed_ids()
        if not seed_ids:
            raise ValueError("No seed-region rows found in dataframe; check seed_regions.")

        resolved_seed_ids = [rid for rid in (self._resolve_to_graph_id(sid) for sid in seed_ids) if rid is not None]
        if not resolved_seed_ids:
            raise ValueError("None of the seed regions could be mapped onto the Allen connectivity graph.")

        resolved_ids = [self._resolve_to_graph_id(region_id) for region_id in self.df['id']]
        self.df['connectivity_resolved_id'] = resolved_ids
        # Distance = # hops for a region to project INTO the seed (afferent/upstream
        # direction), i.e. "regions that project to mPFC" = 1, "regions that project to
        # regions that project to mPFC" = 2, etc. -- NOT how far mPFC's own projections
        # reach outward.
        self.df['connection_distance'] = [
            self.conn_graph.hop_distance(rid, resolved_seed_ids) if rid is not None else np.nan
            for rid in resolved_ids
        ]
        return self.df

    def plot_tvalue_vs_connection_distance(self, stat='t_value', filename_prefix=None):
        filename_prefix = filename_prefix or f'{self.abbreviated_filename}_tval_vs_hops'
        plot_df = self.df.dropna(subset=['connection_distance', stat])
        if plot_df.empty:
            print('No regions with a resolvable connection distance; skipping scatter plot.')
            return None

        X = sm.add_constant(plot_df['connection_distance'].values)
        model = sm.OLS(plot_df[stat].values, X).fit()
        print(f"Connection-distance regression F-value: {model.fvalue:.4f}, p-value: {model.f_pvalue:.4e}")

        plt.figure(figsize=(8, 6))
        plt.scatter(plot_df['connection_distance'], plot_df[stat], alpha=0.6, color='darkorange')
        xs = np.linspace(plot_df['connection_distance'].min(), plot_df['connection_distance'].max(), 50)
        plt.plot(xs, model.predict(sm.add_constant(xs)), color='black', linewidth=2,
                 label=f'OLS fit (p={model.f_pvalue:.3g})')
        plt.xlabel('Connectomic distance from seed region (# synaptic hops)')
        plt.ylabel(f'Average {stat}')
        plt.title(f'{stat} vs. connectomic distance from seed region')
        plt.legend()
        plt.grid(True)
        plt.tight_layout()

        filename = os.path.join(self.drop_directory, f'{filename_prefix}.jpg')
        plt.savefig(filename, dpi=300)
        plt.close()
        return model

    def plot_binned_tvalue_by_hops(self, stat='t_value', filename_prefix=None):
        filename_prefix = filename_prefix or f'{self.abbreviated_filename}_binned_tval_by_hops'
        plot_df = self.df.dropna(subset=['connection_distance', stat])
        if plot_df.empty:
            print('No regions with a resolvable connection distance; skipping binned plot.')
            return None

        grouped = plot_df.groupby('connection_distance')[stat]
        hops = sorted(grouped.groups.keys())
        means = [grouped.get_group(h).mean() for h in hops]
        sems = [sem(grouped.get_group(h)) if len(grouped.get_group(h)) > 1 else 0 for h in hops]

        plt.figure(figsize=(8, 6))
        plt.errorbar(hops, means, yerr=sems, fmt='-o', color='darkorange', ecolor='navajowhite', capsize=4)
        plt.xlabel('Connectomic distance from seed region (# synaptic hops)')
        plt.ylabel(f'Average {stat}')
        plt.title(f'{stat} as a function of connectomic distance (binned by hop count)')
        plt.xticks(hops)
        plt.grid(True)
        plt.tight_layout()

        filename = os.path.join(self.drop_directory, f'{filename_prefix}.jpg')
        plt.savefig(filename, dpi=300)
        plt.close()

        export_df = pd.DataFrame({
            'connection_distance_hops': hops,
            f'{stat}_mean': means,
            f'{stat}_sem': sems,
        })
        csv_filename = os.path.join(self.drop_directory, f'{filename_prefix}.csv')
        export_df.to_csv(csv_filename, index=False)
        return export_df


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Compute connectomic-distance vs. t-value analysis using Allen connectivity data.')
    parser.add_argument('--data-csv', required=True,
                         help='CSV with columns regionname and t_value (one row per region).')
    parser.add_argument('--atlas-path', required=True,
                         help='Path to the atlas drop directory (contains communal_atlas_drop/structures.json).')
    parser.add_argument('--drop-directory', required=True, help='Directory to save plots/CSVs to.')
    parser.add_argument('--filename', default='connectomic_distance.jpg')
    parser.add_argument('--seed-regions', nargs='+',
                         default=['prelimbic', 'infralimbic', 'anterior cingulate'])
    parser.add_argument('--projection-metric', default='normalized_projection_volume')
    parser.add_argument('--edge-threshold', type=float, default=0.01)
    args = parser.parse_args()

    df = pd.read_csv(args.data_csv)
    analysis = ConnectomicDistanceGraph(
        dataframe=df,
        atlas_path=args.atlas_path,
        drop_directory=args.drop_directory,
        filename=args.filename,
        seed_regions=args.seed_regions,
        projection_metric=args.projection_metric,
        edge_threshold=args.edge_threshold,
    )
    analysis()
