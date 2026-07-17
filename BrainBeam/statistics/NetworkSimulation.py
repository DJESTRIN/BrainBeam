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
from scipy import stats
import itertools
import statsmodels.api as sm
from statsmodels.formula.api import ols
import ipdb

def custom_naming(region_name: str) -> str:
    r_lower = region_name.lower()

    # --- Medial Prefrontal Cortex (distinct) ---
    if any(sub in r_lower for sub in [
        'prelimbic', 'infralimbic', 'medial prefrontal', 'anterior cingulate'
    ]):
        return 'mPFC'

    # --- Other Prefrontal / Association ---
    elif any(sub in r_lower for sub in [
        'frontal pole', 'orbital', 'rostrolateral area', 'retrosplenial',
        'dorsal peduncular', 'anterior area'
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
        return 'Hypothalamus/Septum'

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

    # --- Hippocampus / Memory ---
    elif any(sub in r_lower for sub in [
        'perirhinal', 'hippocamp', 'dentate', 'postsubiculum',
        'subiculum', 'hippocampal formation'
    ]):
        return 'Hippocampus/Memory'

    # --- Striatum / Basal Ganglia ---
    elif any(sub in r_lower for sub in [
        'bed nuclei of the stria terminalis', 'bnst', 'stria medullaris',
        'nucleus accumbens', 'caudate', 'putamen', 'globus pallidus'
    ]):
        return 'Striatum/Basal ganglia'

    # --- White matter / Tracts ---
    elif any(sub in r_lower for sub in [
        'corpus callosum', 'cingulum', 'pyramid', 'tract', 'fornix'
    ]):
        return 'White matter/Tracts'

    # --- Olfactory ---
    elif 'olfactory' in r_lower:
        return 'Olfactory'

    # --- Gustatory ---
    elif 'gustatory' in r_lower or 'insular' in r_lower:
        return 'Gustatory'

    # --- Default ---
    else:
        return 'Other'

def compare_networks_bootstrap(boot_metrics_dict, full_graphs=None, top_n=10, output_csv="network_metrics_long.csv", posthoc_csv="network_posthoc.csv"):
    """
    Compare networks using bootstrapped distributions for all metrics and save data for R plotting.

    Parameters
    ----------
    boot_metrics_dict : dict
        Dictionary {group: bootstrapped metrics DataFrame from network.bootstrap_network_metrics()}.
    full_graphs : dict, optional
        Dictionary {group: full networkx graph} for node-level metrics.
    top_n : int
        Number of top regions to consider by degree.
    output_csv : str
        File path to save long-format CSV with mean ± SEM.
    posthoc_csv : str
        File path to save post-hoc test results.

    Returns
    -------
    df_long : pd.DataFrame
        Tall-format DataFrame with all metrics (mean ± SEM) ready for plotting.
    df_posthoc : pd.DataFrame
        Post-hoc test results (ANOVA + pairwise) per metric/region.
    """
    df_list = []
    network_metrics = ['n_nodes', 'n_edges', 'avg_degree', 'avg_clustering', 'density']
    network_boot_summaries = {}
    node_boot_values = {}

    for grp, boot_df in boot_metrics_dict.items():
        if boot_df.empty:
            continue

        network_summary = (
            boot_df
            .groupby('bootstrap_id', as_index=False)
            .agg(
                n_nodes=('n_nodes', 'first'),
                n_edges=('n_edges', 'first'),
                avg_degree=('degree', 'mean'),
                avg_clustering=('clustering', 'mean'),
                density=('density', 'first')
            )
        )
        network_boot_summaries[grp] = network_summary

        for metric in network_metrics:
            metric_vals = network_summary[metric].dropna().to_numpy()
            n_boot = len(metric_vals)
            mean_val = np.mean(metric_vals) if n_boot else np.nan
            sem_val = np.std(metric_vals, ddof=1) / np.sqrt(n_boot) if n_boot > 1 else 0
            df_list.append({
                'metric': metric,
                'region': np.nan,
                'condition': grp,
                'mean': mean_val,
                'sem': sem_val,
                'n_boot': n_boot
            })

        if full_graphs is not None and grp in full_graphs:
            G = full_graphs[grp]
            degrees = dict(G.degree())
            top_deg = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:top_n]

            for region, deg in top_deg:
                node_vals = boot_df.loc[boot_df['region'] == region, 'degree'].dropna().to_numpy()
                node_boot_values[(grp, region)] = node_vals
                n_boot = len(node_vals)
                mean_val = np.mean(node_vals) if n_boot else deg
                sem_val = np.std(node_vals, ddof=1) / np.sqrt(n_boot) if n_boot > 1 else 0
                df_list.append({
                    'metric': 'degree',
                    'region': region,
                    'condition': grp,
                    'mean': mean_val,
                    'sem': sem_val,
                    'n_boot': n_boot
                })

    df_long = pd.DataFrame(df_list)
    df_long.to_csv(output_csv, index=False)

    # --- Post-hoc tests: ANOVA + pairwise comparisons ---
    posthoc_results = []
    for metric in df_long['metric'].unique():
        df_metric = df_long[df_long['metric'] == metric]

        if df_metric['region'].isna().all():
            boot_data = []
            for grp in df_metric['condition'].unique():
                vals = network_boot_summaries[grp][metric].dropna().to_numpy()
                if len(vals):
                    boot_data.append(pd.DataFrame({'value': vals, 'condition': grp}))
            if len(boot_data) < 2:
                continue
            df_anova = pd.concat(boot_data)
            model = ols('value ~ C(condition)', data=df_anova).fit()
            anova_table = sm.stats.anova_lm(model, typ=2)
            p_anova = anova_table['PR(>F)'].values[0]
            posthoc_results.append({
                'metric': metric,
                'region': np.nan,
                'comparison': 'ANOVA',
                'p_value': p_anova
            })

            for grp1, grp2 in itertools.combinations(df_metric['condition'].unique(), 2):
                vals1 = network_boot_summaries[grp1][metric].dropna().to_numpy()
                vals2 = network_boot_summaries[grp2][metric].dropna().to_numpy()
                t_stat, p_val = stats.ttest_ind(vals1, vals2, equal_var=False)
                posthoc_results.append({
                    'metric': metric,
                    'region': np.nan,
                    'comparison': f'{grp1} vs {grp2}',
                    'p_value': p_val
                })
        else:
            for region in df_metric['region'].dropna().unique():
                df_region = df_metric[df_metric['region']==region]
                boot_data = []
                for grp in df_region['condition'].unique():
                    vals = node_boot_values.get((grp, region))
                    if vals is not None and len(vals):
                        boot_data.append(pd.DataFrame({'value': vals, 'condition': grp}))
                if len(boot_data) < 2:
                    continue
                df_anova = pd.concat(boot_data)
                model = ols('value ~ C(condition)', data=df_anova).fit()
                anova_table = sm.stats.anova_lm(model, typ=2)
                p_anova = anova_table['PR(>F)'].values[0]
                posthoc_results.append({
                    'metric': 'degree',
                    'region': region,
                    'comparison': 'ANOVA',
                    'p_value': p_anova
                })

                # Pairwise t-tests
                conditions = df_anova['condition'].unique()
                for grp1, grp2 in itertools.combinations(conditions, 2):
                    vals1 = df_anova.loc[df_anova['condition']==grp1,'value'].values
                    vals2 = df_anova.loc[df_anova['condition']==grp2,'value'].values
                    t_stat, p_val = stats.ttest_ind(vals1, vals2, equal_var=False)
                    posthoc_results.append({
                        'metric': 'degree',
                        'region': region,
                        'comparison': f'{grp1} vs {grp2}',
                        'p_value': p_val
                    })

    df_posthoc = pd.DataFrame(posthoc_results)
    df_posthoc.to_csv(posthoc_csv, index=False)

    return df_long, df_posthoc

class network:
    def __init__(self, dataframe, threat_dict, custom_grouping_dict, 
                 origin=None, origin_name='mPFC', groups=['water','vanilla','tmt'], 
                 correlation_threshold=0.2, top_n=100, 
                 bootstrap_n=1000, sample_size=None, seed=0):
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
        self.bootstrap_n = bootstrap_n
        self.sample_size = sample_size
        self.rng = np.random.default_rng(seed)
        self.group_colors = {'water': '#5c6bc0', 'vanilla': '#ffcc66', 'tmt': '#a83232'}

    def __call__(self):

        # Generate example graph layout
        full_graphs = {}
        full_corr_mats = {}
        full_dfs = {}
        for i, grp in enumerate(self.groups):
            df_grp, corr_mat, _ = self.correlation_dataframe(group_index=i)
            G = self.generate_graph(corr_mat, df_grp)
            full_graphs[grp] = G
            full_corr_mats[grp] = corr_mat
            full_dfs[grp] = df_grp

        G_list = list(full_graphs.values())
        sizes_list = self.compute_normalized_node_sizes(G_list)

        for i, grp in enumerate(self.groups):
            color = self.group_colors.get(grp, "#FF0000")
            self.plot_graph(
                full_graphs[grp],
                filename=f'{grp}_graph.jpg', 
                node_color=color,
                sizes=[j + 20 for j in sizes_list[i]]
            )

        # Bootstrap Graph Theory 
        boot_long_df = self.bootstrap_network_metrics()  
        boot_long_df.to_csv("bootstrapped_network_stats_long.csv", index=False)

        # Summary statistics on boot strapped graphs
        boot_metrics_dict = {grp: boot_long_df[boot_long_df['condition'] == grp] for grp in self.groups}
        summary_df, top_regions_df = compare_networks_bootstrap(boot_metrics_dict,full_graphs=full_graphs,top_n=10)
        return summary_df, top_regions_df

    def add_gaussian_noise(self, df, value_col, group_cols, rng, noise_frac=0.1):
        df = df.copy()

        for _, idx in df.groupby(group_cols).groups.items():
            vals = df.loc[idx, value_col].values
            if len(vals) < 2:
                continue

            sigma = np.std(vals, ddof=1)
            if sigma == 0:
                continue

            noise = rng.normal(0, noise_frac * sigma, size=len(vals))
            df.loc[idx, value_col] += noise

        return df


    def bootstrap_network_metrics(self):
        """ Network metric dataset based on bootstrapping."""

        rows = []  
        for grp_idx, grp in enumerate(self.groups):
            df_grp = self.df[self.df['group'] == grp]
            suids = df_grp['suid'].unique()
            n_suids = len(suids)

            for boot_id in range(self.bootstrap_n):

                # Generate a random sample boot strapped based on data with some random noise
                max_drop = max(n_suids - 3, 1)  
                k = self.rng.integers(1, max_drop + 1)
                actual_sample_size = n_suids - k
                sampled_suids = self.rng.choice(suids, size=actual_sample_size, replace=False)
                df_sample = df_grp[df_grp['suid'].isin(sampled_suids)]
                df_sample = self.add_gaussian_noise(df_sample,'rawcount', group_cols=['regionname', 'group'],rng=self.rng, noise_frac=0.1)

                # Graph for current boot strap dataset
                df_boot, corr_mat, _ = self.correlation_dataframe(group_index=grp_idx, df=df_sample)
                G = self.generate_graph(corr_mat, df_boot)

                # Concat Metrics
                degrees = dict(G.degree())
                clustering = nx.clustering(G)
                strengths = dict(G.degree(weight="weight")) if len(list(G.edges(data=True))) else None
                for region in G.nodes():
                    rows.append({
                        "bootstrap_id": boot_id,
                        "condition": grp,
                        "region": region,
                        "degree": degrees.get(region),
                        "clustering": clustering.get(region),
                        "strength": strengths.get(region) if strengths is not None else None,
                        "n_nodes": G.number_of_nodes(),
                        "n_edges": G.number_of_edges(),
                        "density": nx.density(G)
                    })

        return pd.DataFrame(rows)

    def correlation_dataframe(self, group_index, top_corr_regions=None, df=None):
        """
        If df is provided, use it instead of pulling from self.df.
        """
        if df is None:
            df_control = self.df[self.df['group'] == self.groups[group_index]]
        else:
            df_control = df.copy()

        df_pivot = df_control.pivot_table(
            index='suid', columns='regionname', values='rawcount', aggfunc='mean')
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

        if 'White matter/Tracts' in df_top_grouped.columns:
            df_top_grouped = df_top_grouped.drop(columns='White matter/Tracts')

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
            sizes_list.append(np.nan_to_num(np.array(sizes), nan=200).tolist())
        return sizes_list

    def plot_graph(self, G, filename, node_color="#FF0000", highlight_nodes=['mPFC'], 
               show_labels=False, sizes=None):
        pos = nx.spring_layout(G, weight='weight', k=1.0, iterations=200, seed=42)

        if sizes is None:
            # Base node size factor: adjust 100–200 for visibility
            base_size = 500
            sizes = [base_size + G.degree(n, weight='weight')*400 for n in G.nodes]

        # Ensure no NaNs
        sizes = np.nan_to_num(np.array(sizes), nan=200).tolist()

        colors = [('#1b9e77' if n in highlight_nodes else node_color) for n in G.nodes]

        edges = G.edges(data=True)
        edge_widths = [abs(d['weight']) * 5 for (_, _, d) in edges]  # reduce scale if too thick
        edge_color = "#888888"

        plt.figure(figsize=(10, 8))
        nx.draw(
            G, pos,
            with_labels=show_labels,
            node_size=sizes,
            node_color=colors,
            edgecolors='black',
            linewidths=6,
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
    
    raise SystemExit(
        "This example block is incomplete: load a dataframe and instantiate "
        "network(...) from another script or notebook."
    )