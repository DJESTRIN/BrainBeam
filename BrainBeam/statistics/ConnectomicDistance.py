#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: ConnectomicDistance.py
Description:
    Region-level analogue of the physical-distance-from-seed analysis in
    AtlasGraphics.py. Instead of Euclidean voxel distance from a seed region
    (default: mPFC), the "distance" assigned to each region is the number of
    synaptic hops separating it from the seed, based on the Allen Mouse Brain
    Connectivity Atlas. E.g. if mPFC projects directly to a region, that
    region gets a connectomic distance of 1; if mPFC only reaches a region via
    one intermediate region, that region gets a connectomic distance of 2.

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
        # Preserve order but drop duplicates
        self.structure_ids = list(dict.fromkeys(int(s) for s in structure_ids))
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self.manifest_file = manifest_file or os.path.join(
            self.cache_dir, 'mouse_connectivity_manifest.json')
        self.projection_metric = projection_metric
        self.edge_threshold = edge_threshold
        self.hemisphere_id = hemisphere_id
        self.graph = None

    def build(self):
        """Fetch the structure x structure projection matrix and threshold it into a directed graph."""
        mcc = MouseConnectivityCache(manifest_file=self.manifest_file)
        matrix_info = mcc.get_projection_matrix(
            structure_ids=self.structure_ids,
            hemisphere_ids=[self.hemisphere_id],
            parameter=self.projection_metric,
            row_structure_ids=self.structure_ids,
            column_structure_ids=self.structure_ids,
        )
        matrix = matrix_info['matrix']
        row_ids = [r['structure_id'] for r in matrix_info['rows']]
        col_ids = [c['structure_id'] for c in matrix_info['columns']]

        graph = nx.DiGraph()
        graph.add_nodes_from(self.structure_ids)
        for i, source_id in enumerate(row_ids):
            for j, target_id in enumerate(col_ids):
                weight = matrix[i, j]
                if source_id != target_id and weight >= self.edge_threshold:
                    graph.add_edge(source_id, target_id, weight=float(weight))

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

    def hop_distance(self, source_ids, target_id):
        """
        Minimum number of synaptic hops from any of `source_ids` (e.g. the
        prelimbic/infralimbic/anterior-cingulate sub-structures that make up
        mPFC) to `target_id`. Returns np.nan if no directed path exists or
        `target_id` isn't part of the graph.
        """
        if self.graph is None:
            raise RuntimeError("Call build() (or load()) before computing hop distances.")

        source_ids = [s for s in source_ids if s in self.graph]
        if target_id not in self.graph or not source_ids:
            return np.nan

        best = np.inf
        for source_id in source_ids:
            if source_id == target_id:
                return 0
            try:
                length = nx.shortest_path_length(self.graph, source=source_id, target=target_id)
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
        structure_ids = self.df['id'].unique().tolist()
        self.conn_graph = AllenConnectivityGraph(
            structure_ids=structure_ids,
            cache_dir=self.connectivity_cache_dir,
            projection_metric=self.projection_metric,
            edge_threshold=self.edge_threshold,
        )
        if os.path.exists(self.graph_cache_path):
            self.conn_graph.load(self.graph_cache_path)
        else:
            self.conn_graph.build()
            self.conn_graph.save(self.graph_cache_path)

    def compute_connection_distances(self):
        seed_ids = self._seed_ids()
        if not seed_ids:
            raise ValueError("No seed-region rows found in dataframe; check seed_regions.")

        self.df['connection_distance'] = [
            self.conn_graph.hop_distance(seed_ids, region_id) for region_id in self.df['id']
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
