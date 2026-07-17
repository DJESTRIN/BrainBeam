#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: BrainBeamStats.py
Description: 
Author: David Estrin
Date: 2025-09-08
Version: 2.0
"""
import json
import pandas as pd
import os
import ipdb
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from scipy import stats
from scipy.stats import norm
from itertools import combinations
from mpl_toolkits.axes_grid1.inset_locator import inset_axes, mark_inset
from scipy.stats import pearsonr

# BrainBeam based code
from BrainBeam.statistics.stability import slope_stability as sst 
from BrainBeam.statistics.AtlasGraphics import AtlasGraph
from BrainBeam.statistics.AtlasOperations import AtlasGardener
from BrainBeam.statistics.bootstrap import quick_boot, quick_boot_df
from BrainBeam.statistics.NetworkSimulation import custom_naming, network
from BrainBeam.statistics.threatcomps import plot_mPFC_vs_brain as pmvb

def CohensD(mean1, std1, mean2, std2):
    pooled_std = np.sqrt((std1**2 + std2**2) / 2)
    d = (mean1 - mean2) / pooled_std
    return d

class gen:
    def __init__(self, df, ontology_dict, atlas_path, drop_directory=None, value='normalizedcount', bootstrap=False, 
                 group1='control', group2='cort', group3='none', leveled_atlas=True, restricted_atlas=False, simulation=False, nboot=50, run_stability=True):
        self.df_original = df
        self.df = df
        self.bootstrap = bootstrap
        self.nboot = nboot
        self.value = value
        self.drop_directory = drop_directory
        self.group1 = group1
        self.group2 = group2
        self.group3 = group3
        self.simulation = simulation
        self.atlas_path = atlas_path
        self.run_stability = run_stability

        # Level the atlas with atlas gardender
        if leveled_atlas:
            # Create gardener class
            atobj = AtlasGardener(ontology_dict=ontology_dict,drop_directory=self.drop_directory)
            atobj()

            # Set dataframe brain regions to coarser names for simplicity
            df_regionnames = pd.DataFrame(self.df['regionname'])
            df_regionnames = atobj.map_to_coarsened_atlas(data=df_regionnames)
            self.df['regionname'] = df_regionnames

            # Aggregate region names
            self.df = self.df.groupby(['subject','cage','suid','group', 'channel','lateralization','regionname'], as_index=False)[self.value].sum()

            if restricted_atlas:
                print('A restricted atlas is being used')
                self.df = atobj.restricted_and_coarse_dataframe(dataframe=self.df)
                self.df['rawcount'] = (self.df[self.value] /self.df.groupby('suid')[self.value].transform('sum')) * 100
            else:
                print('Entire atlas being used')
        
        else:
            if restricted_atlas:
                print('A restricted atlas is being used')
                self.df = AtlasGardener.restricted_and_coarse_dataframe(dataframe = self.df)
                self.df['rawcount'] = (self.df[self.value] /self.df.groupby('suid')[self.value].transform('sum')) * 100
            else:
                 print('Entire atlas being used')
        
        if self.bootstrap:
            self.df = quick_boot_df(self.df, n_boot=self.nboot)

        self.df_sum = self.df.groupby(['suid', 'group', 'regionname','lateralization'], as_index=False).agg({self.value: 'sum'})
    
    def __call__(self):
        self.plot_group_average()
        self.plot_distribution()
        self.volcano()
        self.calculate_differences()
        self.grab_differences()
        if self.run_stability:
            self.stability()
        #self.genatlas()

    def plot_group_average(self):
        """
        Compare average normalized count between control and CORT.
        Plots mean ± SEM and prints values.
        """

        # Average per subject first (avoids pseudoreplication)
        df_subject = (
            self.df
            .groupby(['suid', 'group'], as_index=False)[self.value]
            .mean()
        )

        # Split groups
        control = df_subject[df_subject['group'] == self.group1][self.value]
        cort = df_subject[df_subject['group'] == self.group2][self.value]

        # Stats
        control_mean = control.mean()
        cort_mean = cort.mean()
        control_sem = control.std(ddof=1) / np.sqrt(len(control))
        cort_sem = cort.std(ddof=1) / np.sqrt(len(cort))

        t_stat, p_value = stats.ttest_ind(control, cort, equal_var=False)
        n1, n2 = len(control), len(cort)
        s1_sq, s2_sq = control.var(ddof=1), cort.var(ddof=1)
        df = (s1_sq/n1 + s2_sq/n2)**2 / ((s1_sq**2 / (n1**2 * (n1 - 1))) + (s2_sq**2 / (n2**2 * (n2 - 1))))

        print(f"t = {t_stat:.3f}, df = {df:.2f}, p = {p_value:.4f}")

        # Print
        print(f"{self.group1}: {control_mean:.3f} ± {control_sem:.3f}")
        print(f"{self.group2}: {cort_mean:.3f} ± {cort_sem:.3f}")

        # Plot
        plt.figure(figsize=(4, 6))
        plt.bar(
            [self.group1, self.group2],
            [control_mean, cort_mean],
            yerr=[control_sem, cort_sem],
            capsize=6
        )
        plt.ylabel(self.value)
        plt.title("Average Normalized Count ± SEM")
        plt.tight_layout()
        plt.savefig(os.path.join(self.drop_directory, "group_average_normalizedcount.jpg"))

    def plot_distribution(self,filename='hist.jpg'):
        plt.figure(figsize=(10, 10))
        sns.kdeplot(data=self.df, x=str(self.value), hue="group", fill=True, alpha=0.4)
        plt.xlabel("Values")
        plt.ylabel("Density")
        plt.title("Overlapping KDE Plot by Group")
        plt.savefig(os.path.join(self.drop_directory,filename))

    def stability(self):
        self.df_sum.to_csv(os.path.join(self.drop_directory, 'dfsum.csv'))

        # Create dictionaries
        self.sstobjs = {}
        self.sstobjs_simulation = {}
        self.sstobjs_weak = {}
        self.sstobjs_strong = {}

        group_names = self.df_sum['group'].unique().tolist()
        for group1, group2 in combinations(group_names, 2):
            df_pair = self.df_sum[self.df_sum['group'].isin([group1, group2])].reset_index(drop=True)
            label = f"{group1}_vs_{group2}"
            print(label)

            # Gather stability of all data
            obj = sst(dataframe_oh=df_pair, drop_directory=self.drop_directory, xaxis_label=group1, yaxis_label=group2,
                simulation=False, simtrials=10000, convergence_test=False, graph_results=True, regionvarname='regionname',
                groupvarname='group', countvarname=str(self.value), label_oh=f'stability_general_{label}')
            obj()
            self.sstobjs[label] = obj

            # Run simulation to determine individual brain regions contributions
            if self.simulation:
                sim_obj = sst(dataframe_oh=df_pair, drop_directory=self.drop_directory, xaxis_label=group1, yaxis_label=group2,
                    simulation=True, simtrials=10000, convergence_test=True, graph_results=True, regionvarname='regionname',
                    groupvarname='group', countvarname=str(self.value))
                sim_obj()
                self.sstobjs_simulation[label] = sim_obj

            # Look at weak effects
            regions_weak = self.volcano_df[self.volcano_df['effects'] < 0.5]['regionname']
            df_weak = df_pair[df_pair['regionname'].isin(regions_weak)].reset_index(drop=True)
            if not df_weak.empty:
                weak_obj = sst(dataframe_oh=df_weak, drop_directory=self.drop_directory, xaxis_label=group1, yaxis_label=group2,
                    simulation=False, simtrials=10000, convergence_test=False, graph_results=True, regionvarname='regionname',
                    groupvarname='group', countvarname=str(self.value), label_oh=f'weak_effects_{label}')
                weak_obj()
                self.sstobjs_weak[label] = weak_obj

            # Look at strong effects
            regions_strong = self.volcano_df[self.volcano_df['effects'] > 0.5]['regionname']
            df_strong = df_pair[df_pair['regionname'].isin(regions_strong)].reset_index(drop=True)
            if not df_strong.empty:
                strong_obj = sst(dataframe_oh=df_strong,drop_directory=self.drop_directory,xaxis_label=group1,yaxis_label=group2,
                    simulation=False,simtrials=10000,convergence_test=False,graph_results=True,regionvarname='regionname',
                    groupvarname='group',countvarname=str(self.value),label_oh=f'strong_effects_{label}')
                strong_obj()
                self.sstobjs_strong[label] = strong_obj

    def calculate_differences(self):
        regions_oh = self.volcano_df.nlargest(28, 'effects').index
        df_stats_top = self.volcano_df.loc[regions_oh, :]

        # Save largest regions to a file
        csv_filename = os.path.join(self.drop_directory, f'largestregions.csv')
        df_stats_top.to_csv(csv_filename, index=False)
        
        num_rows = len(df_stats_top)
        num_cols = 5  # adjust depending on layout
        num_rows_grid = int(np.ceil(num_rows / num_cols))

        fig, axes = plt.subplots(num_rows_grid, num_cols, figsize=(20, 12))
        axes = axes.flatten()

        for pos, (_, row) in enumerate(df_stats_top.iterrows()):
            ax = axes[pos]

            # Plot the means with error bars
            means = [row['group1mean'], row['group2mean']]
            sems = [row['group1sem'], row['group2sem']]
            label1,label2 = row['comparison'].split(" vs ")
            labels = [label1,label2]

            ax.bar(labels, means, yerr=sems, capsize=5, color=['skyblue', 'lightcoral'])
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

            # Set title or annotations
            annotation = (
                f"{row['regionname']} ({row['lateralization']})\n"
                f"Effect: {row['effects']:.2f}\n"
                f"t = {row['t_value']:.2f}, p = {row['p_value']:.3f}\n"
                f"df = {row['df']:.2f}"
            )
            ax.text(0.05, 0.98, annotation, transform=ax.transAxes,
                fontsize=8, verticalalignment='top')

            ax.set_ylim(0, (max(means) + max(sems)) * 1.3)

        plt.tight_layout()
        plt.savefig(os.path.join(self.drop_directory,'largest_differences.jpg'))

        regions_oh = self.volcano_df.nsmallest(30, 'effects').index
        df_stats_top = self.volcano_df.loc[regions_oh, :]
        
        num_rows = len(df_stats_top)
        num_cols = 5  # adjust depending on layout
        num_rows_grid = int(np.ceil(num_rows / num_cols))

        fig, axes = plt.subplots(num_rows_grid, num_cols, figsize=(20, 12))
        axes = axes.flatten()

        for pos, (_, row) in enumerate(df_stats_top.iterrows()):
            ax = axes[pos]

            # Plot the means with error bars
            means = [row['group1mean'], row['group2mean']]
            sems = [row['group1sem'], row['group2sem']]
            label1,label2 = row['comparison'].split(" vs ")
            labels = [label1,label2]

            ax.bar(labels, means, yerr=sems, capsize=5, color=['skyblue', 'lightcoral'])
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

            # Set title or annotations
            annotation = (
                f"{row['regionname']} ({row['lateralization']})\n"
                f"Effect: {row['effects']:.2f}\n"
                f"t = {row['t_value']:.2f}, p = {row['p_value']:.3f}\n"
                f"df = {row['df']:.2f}"
            )
            ax.text(0.05, 0.98, annotation, transform=ax.transAxes,
                fontsize=8, verticalalignment='top')

            ax.set_ylim(0, (max(means) + max(sems)) * 1.3)

        plt.tight_layout()
        plt.savefig(os.path.join(self.drop_directory,'smallest_differences.jpg'))
    
    def grab_differences(self, n=28):
        """
        Grab top `n` regions by 'effects' for each comparison, excluding fiber/white matter tracts.
        Replaces any removed fiber tracts with the next-highest effects region to maintain `n` rows per group.
        Saves the result as 'largestregionsbygroup.csv' in drop_directory.
        """
        # List of regions considered white matter / fiber tracts
        fiber_tracts = [
            "columns of the fornix",
            "lateral olfactory tract, body",
            "external capsule",
            "spinal tract of the trigeminal nerve",
            "inferior cerebellar peduncle",
            "third ventricle",
            "Superior colliculus, motor related, intermediate white layer",
            "Superior colliculus, zonal layer",
            "cerebral aqueduct"
        ]
        
        def top_n_clean(group):
            # Sort by 'effects' descending
            group_sorted = group.sort_values('effects', ascending=False)
            # Filter out fiber tracts
            group_filtered = group_sorted[~group_sorted['regionname'].isin(fiber_tracts)]
            # Take top n
            return group_filtered.head(n)
        
        # Apply to each comparison
        df_stats_top = self.volcano_df.groupby('comparison', group_keys=False).apply(top_n_clean)
        
        # Save to CSV
        csv_filename = os.path.join(self.drop_directory, 'largestregionsbygroup.csv')
        df_stats_top.to_csv(csv_filename, index=False)

        # Save entire volcano df for easy plotting in R
        csv_filename = os.path.join(self.drop_directory, 'all_volcano_data.csv')
        self.volcano_df.to_csv(csv_filename, index=False)

        return df_stats_top

    def volcano(self, volcano_inset=False):
        # Get unique groups
        groups = [self.group1, self.group2, self.group3]
        
        # Group data by subject, group, region, lateralization
        df_grouped = self.df.groupby(['suid', 'group', 'regionname', 'lateralization'], as_index=False)[self.value].mean()

        fold_changes = []
        p_values = []
        t_values = []
        dfs = []
        effects = []
        group1_mean = []
        group2_mean = []
        group1_sem = []
        group2_sem = []
        region_names = []
        sides = []
        comparisons = []

        for region in df_grouped['regionname'].unique():
            for side in df_grouped['lateralization'].unique():
                region_data = df_grouped[df_grouped['regionname'] == region]
                region_side_data = region_data[region_data['lateralization'] == side]

                # Perform pairwise comparisons among 3 groups
                pairs = [(groups[0], groups[1]), (groups[0], groups[2]), (groups[1], groups[2])]

                for g1, g2 in pairs:
                    group1_data = region_side_data[region_side_data['group'] == g1][self.value]
                    group2_data = region_side_data[region_side_data['group'] == g2][self.value]

                    group1_data = group1_data.dropna()
                    group2_data = group2_data.dropna()

                    # Avoid comparisons if either group has no data
                    if len(group1_data) == 0 or len(group2_data) == 0:
                        continue

                    # Calculate effect size (absolute Cohen's d)
                    effectsize_oh = np.abs(CohensD(mean1=group1_data.mean(),
                                                mean2=group2_data.mean(),
                                                std1=group1_data.std(),
                                                std2=group2_data.std()))
                    # Fold change with +1 to avoid division by zero
                    fold_change = (group1_data.mean() + 1) / (group2_data.mean() + 1)

                    # Two-sample t-test
                    t_stat, p_value = stats.ttest_ind(group1_data, group2_data)
                    n1 = len(group1_data)
                    n2 = len(group2_data)
                    df = n1 + n2 - 2

                    # Append results+
                    effects.append(effectsize_oh)
                    fold_changes.append(fold_change)
                    p_values.append(p_value)
                    t_values.append(t_stat)
                    dfs.append(df)
                    group1_mean.append(group1_data.mean())
                    group2_mean.append(group2_data.mean())
                    group1_sem.append(group1_data.std() / np.sqrt(n1))
                    group2_sem.append(group2_data.std() / np.sqrt(n2))
                    region_names.append(region)
                    sides.append(side)
                    comparisons.append(f"{g1} vs {g2}")

        # Build dataframe for all pairwise comparisons
        self.volcano_df = pd.DataFrame({
            'regionname': region_names,
            'lateralization': sides,
            'fold_change': fold_changes,
            't_value': t_values,
            'p_value': p_values,
            'df': dfs,
            'effects': effects,
            'group1mean': group1_mean,
            'group2mean': group2_mean,
            'group1sem': group1_sem,
            'group2sem': group2_sem,
            'comparison': comparisons
        })

        self.volcano_df['neg_log_p_value'] = -np.log10(self.volcano_df['p_value'])
        volcano_df_sorted = self.volcano_df.sort_values(by='p_value', ascending=True)
        self.top_10_regions = volcano_df_sorted.head(30)

        self.vvt = self.volcano_df[self.volcano_df["comparison"]=="vanilla vs tmt"]
        vvtsorted = self.vvt.sort_values(by='p_value', ascending=True)
        self.vvttop10 = vvtsorted.head(30)

        # Make sure 'comparison' is categorical
        self.volcano_df['comparison'] = self.volcano_df['comparison'].astype('category')

        fig, ax = plt.subplots(figsize=(10, 6))
        sns.scatterplot(
            data=self.volcano_df,
            x='fold_change',
            y='neg_log_p_value',
            hue='comparison',
            palette='tab10',
            edgecolor="black",
            ax=ax
        )

        ax.axhline(y=-np.log10(0.05), color='red', linestyle='--', label='p-value < 0.05')
        ax.axhline(y=-np.log10(0.1), color='green', linestyle='--', label='p-value < 0.1')
        ax.set_title("Volcano Plot: Fold Change vs Significance (Pairwise Comparisons)")
        ax.set_xlabel("Fold Change")
        ax.set_ylabel("-log10(p-value)")

        if volcano_inset:
            for _, row in self.top_10_regions.iterrows():
                ax.annotate(
                    row['regionname'],
                    (row['fold_change'], row['neg_log_p_value']),
                    textcoords="offset points",
                    xytext=(0, 5),
                    ha='center',
                    fontsize=9
                )
            # Do NOT remove legend here if you want to see colors
            # ax.legend().remove()

            inset_ax = inset_axes(ax, width="100%", height="100%", loc='center left',
                                bbox_to_anchor=(0.05, 0.5, 0.1, 0.3), bbox_transform=ax.transAxes)
            sns.scatterplot(
                data=self.volcano_df,
                x='fold_change',
                y='neg_log_p_value',
                hue='comparison',
                palette='tab10',
                edgecolor="black",
                ax=inset_ax
            )
            inset_ax.axvline(x=1, color='black', linestyle='--')
            inset_ax.set_title("")
            inset_ax.set_xlabel("Fold Change")
            inset_ax.set_ylabel("-log10(p-value)")
            inset_ax.legend().remove()

            ax.legend().set_visible(False)
            mark_inset(ax, inset_ax, loc1=2, loc2=4, fc="none", ec="0.5", ls="--")

        # Make sure legend is visible outside the inset condition
        if not volcano_inset:
            ax.legend(title='Comparison groups', loc='best')

        plt.tight_layout()
        plt.savefig(os.path.join(self.drop_directory, 'volcano_updated.jpg'))
  
    def genatlas(self):
        comparisons = [
            ('water vs vanilla', 'tslices_nothreshold_water_vanilla.jpg', 
            np.array([92, 107, 192]), np.array([255, 204, 102])),
            ('water vs tmt', 'tslices_nothreshold_water_tmt.jpg', 
            np.array([92, 107, 192]), np.array([168, 50, 50])),
            ('vanilla vs tmt', 'tslices_nothreshold_vanilla_tmt.jpg', 
            np.array([255, 204, 102]), np.array([168, 50, 50])),
            ('control vs cort', 'tslices_nothreshold_control_cort.jpg', 
            np.array([0, 0, 255]), np.array([255, 0, 0]))]

        for comp, filename, inc_color, dec_color in comparisons:
            dfoh = self.volcano_df[self.volcano_df['comparison'] == comp]
            if dfoh.empty:
                print(f"Skipping {comp} because the dataframe is empty.")
                continue
            self.atob = AtlasGraph(
                dataframe=dfoh, 
                atlas_path=self.atlas_path, 
                drop_directory=self.drop_directory,
                filename=filename,
                default_increase_color=inc_color,
                default_decrease_color=dec_color
            )
            self.atob()

if __name__=='__main__':
    # ================================
    # FosTRAP2 Statistics
    # ================================

    # # User defined inputs
    data_path = r'C:\Users\listo\example_registration_data\test_registration_communal_drop'
    group1_df_path =  r'C:\Users\listo\communal_registration_logcal_drop\salience_experiment\water\df_tall.csv'
    group2_df_path = r'C:\Users\listo\communal_registration_logcal_drop\salience_experiment\vanilla\df_tall.csv'
    group3_df_path = r'C:\Users\listo\communal_registration_logcal_drop\salience_experiment\tmt\df_tall.csv'
    group1_name = 'water'
    group2_name = 'vanilla'
    group3_name = 'tmt'
    output_dir = r'C:\Users\listo\communal_registration_logcal_drop\salience_experiment\results'
    atlas_path = r'C:\Users\listo\communal_registration_logcal_drop\salience_experiment\water'
    keep_channel = ['channel0', 647]  # Keeping channel0 aka channel 647
    restrict_the_atlas = True

    # Get atlas ontology
    drop_atlas_path = os.path.join(data_path,"communal_atlas_drop/")
    atlas_json_file = os.path.join(drop_atlas_path,'structures.json')
    with open(atlas_json_file,'r') as infile:
        ontology_dict = json.load(infile)

    # Read in dataframes and concat them
    df1 = pd.read_csv(group1_df_path)
    df2 = pd.read_csv(group2_df_path)
    df3 = pd.read_csv(group3_df_path)
    df2['group'] = group2_name
    df3['group'] = group3_name
    df = pd.concat([df1,df2,df3])
    df['normalizedcount'] = df['normalizedcount']*100

    # Eliminate unnecessary channels
    if keep_channel:
        df = df[(df['channel'] == keep_channel[0]) | (df['channel'] == keep_channel[1])]

    df = df.reset_index(drop=True)

    # Run data frames through stats
    genobj_fostrap = gen(df=df, ontology_dict=ontology_dict, atlas_path=atlas_path, value='rawcount', drop_directory=output_dir,
                 bootstrap=False, group1=group1_name, group2=group2_name, group3=group3_name, restricted_atlas=restrict_the_atlas,leveled_atlas=False, simulation=False)
    genobj_fostrap()

    # Generate threat graph
    # pmvb(df = genobj_fostrap.df, counttype='rawcount', directory=output_dir)

    # threat_dict = {
    #     "Amygdala": ["amygdala"],
    #     "Hypothalamus": ["hypothalamus"],
    #     "BNST": ["bed nucleus of the stria terminalis", "bed nucl"],
    #     "PAG": ["periaqueductal gray", "periaqueductal"],
    #     "Insula": ["insula"],
    #     "Thalamus": ["thalamus"],
    #     "Hippocampus": ["hippo"],
    #     "Superior Temporal Sulcus": ["superior temporal sulcus"],
    #     "Parietal Cortex": ["parietal cortex", "superior parietal lobule"],
    #     "Cerebellum": ["cerebellum"],
    #     "Lateral Habenula": ["lateral habenula"],
    #     "Dorsal Premammillary Nucleus": ["dorsal premammillary nucleus"]}

    # custom_groups = {
    #     "Somatosensory": ["somatosensory"],
    #     "Visual": ["visual"],
    #     "Auditory": ["auditory"],
    #     "Motor": ["motor"],
    #     "Orbital": ["orbital"]}
    
    # network_object = network(dataframe=genobj_fostrap.df, threat_dict=threat_dict, custom_grouping_dict=custom_groups, 
    #        origin=None, origin_name = 'mPFC', groups=['water','vanilla','tmt'], 
    #        correlation_threshold=0.2, top_n=100)
    # network_object()


    # ================================
    # Rabies Statistics
    # ================================

    # User defined inputs
    data_path = r'C:\Users\listo\example_registration_data\test_registration_communal_drop'
    group1_df_path =  r'C:\Users\listo\communal_registration_logcal_drop\rabies_experiment\control\df_tall.csv'
    group2_df_path = r'C:\Users\listo\communal_registration_logcal_drop\rabies_experiment\experimental\df_tall.csv'
    group1_name = 'control'
    group2_name = 'cort'
    output_dir = r'C:\Users\listo\communal_registration_logcal_drop\rabies_experiment\results2'
    atlas_path = r'C:\Users\listo\communal_registration_logcal_drop\rabies_experiment\experimental'
    keep_channel = [647]
    restrict_the_atlas = True

    # Get atlas ontology
    drop_atlas_path = os.path.join(data_path,"communal_atlas_drop/")
    atlas_json_file = os.path.join(drop_atlas_path,'structures.json')
    with open(atlas_json_file,'r') as infile:
        ontology_dict = json.load(infile)

    # Read in dataframes and concat them
    df = pd.read_csv(group1_df_path)
    df2 = pd.read_csv(group2_df_path)
    df2['group'] = group2_name
    df = pd.concat([df,df2])
    df['normalizedcount'] = df['normalizedcount']*100

    # Eliminate unnecessary channels
    if keep_channel:
        df = df[df['channel'] == keep_channel[0]]

    # Run data frames through stats
    genobj_rabies = gen(df=df, ontology_dict=ontology_dict, atlas_path=atlas_path, value='rawcount', drop_directory=output_dir,
                 bootstrap=False, group1=group1_name, group2=group2_name, restricted_atlas=restrict_the_atlas,leveled_atlas=False, simulation=False, run_stability=False)
    genobj_rabies()

    # output_dir = r'C:\Users\listo\communal_registration_logcal_drop\rabies_experiment\results_boot'
    # os.makedirs(output_dir, exist_ok=True)
    # all_dfs = []
    # df0 = genobj_rabies.volcano_df.copy()
    # df0["nboot"] = 0
    # all_dfs.append(df0)
    # for nboot in [20, 50, 100, 500, 1000, 5000]:
    #     nboot_dir = os.path.join(output_dir, f"nboot_{nboot}")
    #     os.makedirs(nboot_dir, exist_ok=True)
    #     genobj_rabies = gen(df=df, ontology_dict=ontology_dict, atlas_path=atlas_path,
    #                         value='rawcount', drop_directory=nboot_dir,
    #                         bootstrap=True, group1=group1_name, group2=group2_name,
    #                         restricted_atlas=restrict_the_atlas, leveled_atlas=False,
    #                         simulation=True, nboot=nboot, run_stability=False)
    #     genobj_rabies()
    #     local_volcanod_df = genobj_rabies.volcano_df.copy()
    #     local_volcanod_df["nboot"] = nboot
    #     all_dfs.append(local_volcanod_df)
    # final_df = pd.concat(all_dfs, ignore_index=True)
    # final_df.to_csv(os.path.join(output_dir, "volcano_all_bootstraps.csv"), index=False)

    # ================================
    # Rabies and FosTRAP2 Statistics
    # ================================
    merged_df = pd.merge(
        genobj_rabies.volcano_df[['regionname', 'lateralization', 't_value']].rename(columns={'t_value': 't_value_rabies'}),
        genobj_fostrap.volcano_df[['regionname', 'lateralization', 't_value', 'comparison']].rename(columns={'t_value': 't_value_fostrap'}),
        on=['regionname', 'lateralization']).dropna()
    
    # merged_df = merged_df[merged_df['t_value_rabies'].abs() > 2.13]

    def compare_correlations(r1, n1, r2, n2):
        if abs(r1) == 1 or abs(r2) == 1:  # Prevent division by zero
            return np.nan, np.nan
        z1 = np.arctanh(r1)
        z2 = np.arctanh(r2)
        se = np.sqrt(1 / (n1 - 3) + 1 / (n2 - 3))
        z = (z1 - z2) / se
        p = 2 * (1 - norm.cdf(abs(z)))
        return z, p

    reference_comp = 'vanilla vs tmt'
    ref_df = merged_df[merged_df['comparison'] == reference_comp].dropna(subset=['t_value_rabies', 't_value_fostrap'])
    r_ref = ref_df['t_value_rabies'].corr(ref_df['t_value_fostrap'], method='pearson')
    n_ref = len(ref_df)

    for comp in merged_df['comparison'].unique():
        df_filtered = merged_df[merged_df['comparison'] == comp].dropna(subset=['t_value_rabies', 't_value_fostrap'])
        n = len(df_filtered)
        r_pearson = df_filtered['t_value_rabies'].corr(df_filtered['t_value_fostrap'], method='pearson')
        r_spearman = df_filtered['t_value_rabies'].corr(df_filtered['t_value_fostrap'], method='spearman')
        if comp != reference_comp:
            z, p = compare_correlations(r_ref, n_ref, r_pearson, n)
            print(f"Comparison: {comp} — Pearson r = {r_pearson:.3f}, Spearman ρ = {r_spearman:.3f}, n = {n}, z = {z:.3f}, p = {p:.4f}")
        else:
            print(f"Comparison: {comp} — Pearson r = {r_pearson:.3f}, Spearman ρ = {r_spearman:.3f}, n = {n} (reference)")

    vt_df = merged_df[merged_df['comparison'] == 'vanilla vs tmt'].dropna(subset=['t_value_rabies', 't_value_fostrap'])
    r, p = pearsonr(vt_df['t_value_rabies'], vt_df['t_value_fostrap'])
    r2 = r**2
    r_spearman = merged_df['t_value_rabies'].corr(merged_df['t_value_fostrap'], method='spearman')
    print(f"Pearson R = {r:.3f}")
    print(f"R² = {r2:.3f}")
    print(f"p-value = {p:.4e}")
    print(f"Spearman R = {r_spearman:.3f}")
    vt_df.to_csv('FosTrapRabiesCorrelations.csv',index=False)