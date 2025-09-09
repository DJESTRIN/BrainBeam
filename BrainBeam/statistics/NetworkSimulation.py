#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: NetworkSimulation.py
Description: 
Author: David Estrin
Date: 2025-08-25
Version: 1.0
"""
import pandas as pd
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
import seaborn as sns
import ipdb

def custom_naming(region_name: str) -> str:
    r_lower = region_name.lower()

    # --- Prefrontal / Association ---
    if any(sub in r_lower for sub in [
        'frontal pole', 'orbital', 'retrosplenial',
        'dorsal peduncular', 'anterior area', 'rostrolateral area'
    ]):
        return 'Prefrontal/Association'

    # --- Motor ---
    elif any(sub in r_lower for sub in [
        'motor', 'rubrospinal', 'supplemental somatosensory'
    ]):
        return 'Motor'

    # --- Somatosensory ---
    elif 'somatosensory' in r_lower:
        return 'Somatosensory'

    # --- Auditory ---
    elif any(sub in r_lower for sub in [
        'auditory', 'medial geniculate', 'inferior colliculus', 'superior colliculus'
    ]):
        return 'Auditory'

    # --- Visual ---
    elif any(sub in r_lower for sub in [
        'visual', 'lateral geniculate', 'optic tract'
    ]):
        return 'Visual'

    # --- Thalamus ---
    elif any(sub in r_lower for sub in [
        'thalamus', 'thalamic', 'posterior intralaminar',
        'anteroventral nucleus', 'paraventricular nucleus',
        'mediodorsal nucleus', 'central lateral nucleus',
        'central medial nucleus', 'nucleus of reuniens',
        'external medullary lamina'
    ]):
        return 'Thalamus'

    # --- Hypothalamus / Septum ---
    elif any(sub in r_lower for sub in [
        'tuberomammillary', 'ventral premammillary', 'dorsal premammillary',
        'medial mammillary', 'preoptic', 'lateral septal',
        'parataenial', 'precommissural', 'subparafascicular'
    ]):
        return 'Hypothalamus'

    # --- Midbrain / Brainstem ---
    elif any(sub in r_lower for sub in [
        'periaqueductal', 'pag', 'midbrain', 'pons', 'medulla',
        'tegmental', 'pretectal', 'parabigeminal', 'nucleus raphe',
        'retrorubral', 'darkschewitsch', 'sublaterodorsal'
    ]):
        return 'Midbrain/Brainstem'

    # --- Cerebellum ---
    elif any(sub in r_lower for sub in [
        'simple lobule', 'lobule', 'cerebellum', 'middle cerebellar peduncle'
    ]):
        return 'Cerebellum'

    # --- Hippocampal / Memory ---
    elif any(sub in r_lower for sub in [
        'perirhinal', 'hippocamp', 'dentate', 'postsubiculum',
        'subiculum', 'hippocampal formation'
    ]):
        return 'Hippocampus/Memory'

    # --- Striatum / Basal Ganglia ---
    elif any(sub in r_lower for sub in [
        'bed nuclei of the stria terminalis', 'bnst', 'stria medullaris',
        'nucleus accumbens'
    ]):
        return 'Striatum/Basal ganglia'

    # --- White matter tracts / commissures ---
    elif any(sub in r_lower for sub in [
        'corpus callosum', 'cingulum', 'pyramid', 'tract'
    ]):
        return 'White matter/Tracts'

    # --- Olfactory ---
    elif 'olfactory' in r_lower:
        return 'Olfactory'

    # --- Gustatory ---
    elif 'gustatory' in r_lower:
        return 'Gustatory'

    # --- Default ---
    else:
        return 'Other'


def compare_networks(condition_graphs, top_n=10, corr_threshold=0.3, n_permutations=1000, seed=0, plot=True):
    """
    Compare network properties across experimental conditions, 
    with permutation-based p-values for overlaps and node degrees.
    Optionally plots results.

    Parameters
    ----------
    condition_graphs : dict
        Dictionary mapping condition name -> (df, corr_matrix, graph)
    top_n : int
        Number of top regions to report by degree.
    corr_threshold : float
        Correlation cutoff to consider edges for overlap.
    n_permutations : int
        Number of permutations for null distributions.
    seed : int
        Random seed for reproducibility.
    plot : bool
        Whether to generate summary plots.

    Returns
    -------
    summary_df : pd.DataFrame
        Network-level metrics by condition.
    overlap_df : pd.DataFrame
        Edge overlaps across conditions (with p-values).
    top_regions_df : pd.DataFrame
        Top N regions by degree for each condition (with p-values).
    """
    rng = np.random.default_rng(seed)
    summary_stats = []
    top_regions = []
    edge_sets = {}
    null_distributions = {}

    for cond, (df, corr, G) in condition_graphs.items():
        # --- Summary network stats
        stats = {
            "condition": cond,
            "n_nodes": G.number_of_nodes(),
            "n_edges": G.number_of_edges(),
            "avg_degree": sum(dict(G.degree()).values()) / G.number_of_nodes(),
            "avg_clustering": nx.average_clustering(G),
            "density": nx.density(G),
        }
        summary_stats.append(stats)

        # --- Degrees
        degrees = dict(G.degree())
        top_deg = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:top_n]

        # Null distribution for degrees
        deg_null = {node: [] for node in G.nodes()}
        A = nx.to_numpy_array(G)
        nodes = list(G.nodes())
        for _ in range(n_permutations):
            A_perm = A.copy()
            rng.shuffle(A_perm.flat)
            G_perm = nx.from_numpy_array(A_perm > 0)
            mapping = dict(zip(range(len(nodes)), nodes))
            G_perm = nx.relabel_nodes(G_perm, mapping)
            perm_degrees = dict(G_perm.degree())
            for node in deg_null:
                deg_null[node].append(perm_degrees.get(node, 0))
        null_distributions[cond] = deg_null

        for region, deg in top_deg:
            null_vals = np.array(deg_null[region])
            p_val = (np.sum(null_vals >= deg) + 1) / (n_permutations + 1)
            top_regions.append({
                "condition": cond,
                "region": region,
                "degree": deg,
                "p_value": p_val
            })

        # --- Collect edges above threshold
        edges = set()
        for u, v, w in G.edges(data="weight", default=1.0):
            if abs(w) >= corr_threshold:
                edges.add(tuple(sorted((u, v))))
        edge_sets[cond] = edges

    # --- Convert to DataFrames
    summary_df = pd.DataFrame(summary_stats)
    top_regions_df = pd.DataFrame(top_regions)

    # --- Compute pairwise overlaps
    overlap_records = []
    conds = list(edge_sets.keys())
    for i in range(len(conds)):
        for j in range(i+1, len(conds)):
            c1, c2 = conds[i], conds[j]
            e1, e2 = edge_sets[c1], edge_sets[c2]
            overlap = len(e1 & e2)
            only_c1 = len(e1 - e2)
            only_c2 = len(e2 - e1)
            union = len(e1 | e2)
            jaccard = overlap / union if union > 0 else 0

            # --- permutation test for overlaps ---
            shared_null = []
            nodes_c2 = list(condition_graphs[c2][2].nodes())
            for _ in range(n_permutations):
                rng.shuffle(nodes_c2)
                mapping = dict(zip(condition_graphs[c2][2].nodes(), nodes_c2))
                G2_perm = nx.relabel_nodes(condition_graphs[c2][2], mapping)
                e2_perm = set(tuple(sorted(edge)) for edge in G2_perm.edges())
                shared_null.append(len(e1 & e2_perm))
            shared_null = np.array(shared_null)
            p_val = (np.sum(shared_null >= overlap) + 1) / (n_permutations + 1)

            overlap_records.append({
                "cond1": c1, "cond2": c2,
                "shared_edges": overlap,
                f"unique_{c1}": only_c1,
                f"unique_{c2}": only_c2,
                "jaccard_index": jaccard,
                "p_value": p_val
            })
    overlap_df = pd.DataFrame(overlap_records)

    # --- PLOTTING ---
    if plot:
        sns.set(style="whitegrid")

        # 1. Summary metrics
        fig, axes = plt.subplots(1, 3, figsize=(18,5))
        sns.barplot(data=summary_df, x="condition", y="avg_degree", ax=axes[0])
        axes[0].set_title("Average Degree")
        sns.barplot(data=summary_df, x="condition", y="avg_clustering", ax=axes[1])
        axes[1].set_title("Average Clustering")
        sns.barplot(data=summary_df, x="condition", y="density", ax=axes[2])
        axes[2].set_title("Density")
        plt.tight_layout()
        plt.savefig('summarys.jpg')

        # 2. Top regions by degree
        for cond in top_regions_df["condition"].unique():
            df_cond = top_regions_df[top_regions_df["condition"] == cond].sort_values("degree", ascending=False)
            plt.figure(figsize=(10,4))
            sns.barplot(data=df_cond, x="region", y="degree", palette="viridis")
            for i, row in enumerate(df_cond.itertuples()):
                if row.p_value < 0.05:
                    plt.text(i, row.degree+0.1, "*", ha='center', va='bottom', color='red', fontsize=14)
            plt.title(f"Top {top_n} regions by degree ({cond})")
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(f'topregions{cond}.jpg')

        # 3. Pairwise Jaccard overlaps heatmap
        jaccard_mat = pd.DataFrame(0, index=conds, columns=conds, dtype=float)
        for _, row in overlap_df.iterrows():
            jaccard_mat.loc[row.cond1, row.cond2] = row.jaccard_index
            jaccard_mat.loc[row.cond2, row.cond1] = row.jaccard_index
        plt.figure(figsize=(6,5))
        sns.heatmap(jaccard_mat, annot=True, fmt=".2f", cmap="Blues")
        plt.title("Pairwise Edge Jaccard Index")
        plt.savefig('heatmap.jpg')

    return summary_df, overlap_df, top_regions_df


class network:
    def __init__(self, dataframe, threat_dict, custom_grouping_dict, 
                 origin=None, origin_name='mPFC', groups=['water','vanilla','tmt'], 
                 correlation_threshold=0.2, top_n=100):
        self.df = dataframe
        self.threat_dict = threat_dict
        self.custom_grouping_dict = custom_grouping_dict

        self.origin = origin
        self.origin_name = origin_name
        if self.origin is None:
            self.origin = ["anterior cingulate", "prelimbic", "infralimb"]

        self.groups = groups
        self.correlation_threshold = correlation_threshold
        self.top_n = top_n

    def __call__(self):
        # --- Correlation data and graphs ---
        df_water, corr_water, top_corr_regions = self.correlation_dataframe(group_index=0)
        G_water = self.generate_graph(corr_water, df_water)

        df_vanilla, corr_vanilla, __ = self.correlation_dataframe(group_index=1, top_corr_regions=top_corr_regions)
        G_vanilla = self.generate_graph(corr_vanilla, df_vanilla)

        df_tmt, corr_tmt, __ = self.correlation_dataframe(group_index=2, top_corr_regions=top_corr_regions)
        G_tmt = self.generate_graph(corr_tmt, df_tmt)

        # --- Normalize node sizes across all graphs ---
        G_list = [G_water, G_vanilla, G_tmt]
        sizes_list = self.compute_normalized_node_sizes(G_list)
        sizes_list = [number + 5000 for sublist in sizes_list for number in sublist]

        # --- Plot graphs ---
        self.plot_graph(G_water, filename='water_graph.jpg', node_color="#5c6bc0", sizes=sizes_list[0])
        self.plot_graph(G_vanilla, filename='vanilla_graph.jpg', node_color="#ffcc66", sizes=sizes_list[1])
        self.plot_graph(G_tmt, filename='tmt_graph.jpg', node_color="#a83232", sizes=sizes_list[2])

        # --- Compare networks ---
        summary_df, overlap_df, top_regions_df = compare_networks({
            "water": (df_water, corr_water, G_water),
            "vanilla": (df_vanilla, corr_vanilla, G_vanilla),
            "tmt": (df_tmt, corr_tmt, G_tmt)
        }, top_n=10, corr_threshold=0.3)

    def correlation_dataframe(self, group_index, top_corr_regions=None):
        df_control = self.df[self.df['group'] == self.groups[group_index]]
        df_pivot = df_control.pivot_table(
            index='suid', columns='regionname', values='normalizedcount', aggfunc='mean'
        )
        df_pivot.columns = df_pivot.columns.map(str)

        # Collapse origin
        origin = [col for col in df_pivot.columns if any(sub in col.lower() for sub in self.origin)]
        if not origin:
            raise ValueError("No origin regions found with specified substrings")
        df_pivot[self.origin_name] = df_pivot[origin].sum(axis=1)
        df_pivot.drop(columns=origin, inplace=True)

        # Correlations wrt origin
        if top_corr_regions is None:
            corr_with_origin = df_pivot.corr()[self.origin_name].drop(self.origin_name)
            top_corr_regions = corr_with_origin.sort_values(ascending=False).head(self.top_n).index.tolist()

        # Top correlated regions
        valid_top_corr = [r for r in top_corr_regions if r in df_pivot.columns]
        df_top = df_pivot[valid_top_corr].copy()
        mapping = {col: custom_naming(col) for col in df_top.columns}
        df_top_grouped = df_top.groupby(mapping, axis=1).sum()

        # Final dataframe
        cols_to_concat = [df_pivot[self.origin_name]]
        if "mPFC" in df_pivot.columns:
            cols_to_concat.append(df_pivot["mPFC"])
        cols_to_concat.append(df_top_grouped)
        df_plot = pd.concat(cols_to_concat, axis=1)
        df_plot = df_plot.loc[:, ~df_plot.columns.duplicated()]

        corr_mat = df_plot.corr()
        return df_plot, corr_mat, top_corr_regions

    def generate_graph(self, correlation_matrix, dataframe):
        G = nx.Graph()
        for region in dataframe.columns:
            G.add_node(region, size=dataframe[region].mean())

        for i, r1 in enumerate(dataframe.columns):
            for j, r2 in enumerate(dataframe.columns):
                if i >= j:
                    continue
                weight = correlation_matrix.at[r1, r2]
                if abs(weight) >= self.correlation_threshold:
                    G.add_edge(r1, r2, weight=weight)

        return G

    def compute_normalized_node_sizes(self, G_list, min_size=400, max_size=1500):
        # Collect all degrees across graphs
        all_degrees = []
        for G in G_list:
            all_degrees.extend([G.degree(n, weight='weight') for n in G.nodes])
        global_min = min(all_degrees)
        global_max = max(all_degrees)

        sizes_list = []
        for G in G_list:
            sizes = []
            for n in G.nodes:
                deg = G.degree(n, weight='weight')
                if global_max > global_min:
                    size = min_size + (deg - global_min) / (global_max - global_min) * (max_size - min_size)
                else:
                    size = min_size
                sizes.append(size)
            sizes = np.nan_to_num(np.array(sizes), nan=200).tolist()
            sizes_list.append(sizes)
        return sizes_list

    def plot_graph(self, G, filename, node_color="#FF0000", highlight_nodes=['mPFC'], 
               show_labels=False, sizes=None):
        """
        Plot network graph with publication-ready aesthetics and optional precomputed node sizes.
        
        Parameters
        ----------
        G : networkx.Graph
            Weighted graph with edge weights as correlation coefficients.
        filename : str
            Output filename for saved figure.
        node_color : str
            Hex color for regular nodes.
        highlight_nodes : list
            Nodes to highlight (e.g., mPFC).
        show_labels : bool
            Whether to show node labels.
        sizes : list or None
            Precomputed node sizes. If None, will calculate from degree.
        """

        # --- Layout ---
        pos = nx.spring_layout(G, weight='weight', k=1.0, iterations=200, seed=42)

        # --- Node sizes ---
        if sizes is None:
            sizes = [max(np.sqrt(G.degree(n, weight='weight'))*5000, 1000) for n in G.nodes]
            sizes = np.nan_to_num(np.array(sizes), nan=200).tolist()

        # --- Node colors ---
        colors = [('#ff33cc' if n in highlight_nodes else node_color) for n in G.nodes]

        # --- Edge widths and color ---
        edges = G.edges(data=True)
        edge_widths = [abs(d['weight']) * 10 for (_, _, d) in edges]
        edge_color = "#888888"

        # --- Dynamic figure size based on layout spread ---
        x_vals = [p[0] for p in pos.values()]
        y_vals = [p[1] for p in pos.values()]
        x_span = max(x_vals) - min(x_vals)
        y_span = max(y_vals) - min(y_vals)
        scale_factor = 10
        fig_width = max(8, x_span * scale_factor)
        fig_height = max(6, y_span * scale_factor)

        # --- Plot ---
        plt.figure(figsize=(fig_width, fig_height))
        nx.draw(
            G, pos,
            with_labels=show_labels,
            node_size=sizes,
            node_color=colors,
            edgecolors='black',
            linewidths=10,
            width=edge_widths,
            edge_color=edge_color,
            alpha=0.9,
            font_size=12
        )
        plt.tight_layout()
        plt.savefig(filename, dpi=300)
        plt.close()








if __name__ == '__main__':
    threat_dict = {
        "Amygdala": ["amygdala"],
        "Hypothalamus": ["hypothalamus"],
        "BNST": ["bed nucleus of the stria terminalis", "bed nucl"],
        "PAG": ["periaqueductal gray", "periaqueductal"],
        "Insula": ["insula"],
        "Thalamus": ["thalamus"],
        "Hippocampus": ["hippo"],
        "Superior Temporal Sulcus": ["superior temporal sulcus"],
        "Parietal Cortex": ["parietal cortex", "superior parietal lobule"],
        "Cerebellum": ["cerebellum"],
        "Lateral Habenula": ["lateral habenula"],
        "Dorsal Premammillary Nucleus": ["dorsal premammillary nucleus"]}

    custom_groups = {
        "Somatosensory": ["somatosensory"],
        "Visual": ["visual"],
        "Auditory": ["auditory"],
        "Motor": ["motor"],
        "Orbital": ["orbital"]}
    
    network(dataframe, threat_dict, custom_grouping_dict=custom_groups, 
            origin=None, origin_name = 'mPFC', groups=['water','vanilla','tmt'], 
            correlation_threshold=0.2, top_n=100)