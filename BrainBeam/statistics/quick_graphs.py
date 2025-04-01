#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: concatdataframe.py
Description: 
Author: David Estrin
Date: 2024-008-15
Version: 1.0
"""
import pandas as pd
import os
import ipdb
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from scipy import stats
from mpl_toolkits.axes_grid1.inset_locator import inset_axes, mark_inset
from BrainBeam.statistics.stability import slope_stability as sst 

class gen:
    def __init__(self, df, drop_directory=None, value='normalizedcount'):
        self.df = df
        self.value = value
        self.drop_directory = drop_directory
        self.df_sum = df.groupby(['suid', 'group', 'regionname', 'regionid'], as_index=False).agg({self.value: 'sum'})
    
    def __call__(self):
        self.plot_distribution()

    def plot_distribution(self,filename='hist.jpg'):
        plt.figure(figsize=(10, 10))
        sns.kdeplot(data=df, x="normalizedcount", hue="group", fill=True, alpha=0.4)
        plt.xlabel("Values")
        plt.ylabel("Density")
        plt.title("Overlapping KDE Plot by Group")
        plt.savefig(os.path.join(self.drop_directory,filename))

    def stability(self):
        self.sstobj = sst(dataframe_oh=self.df_sum, drop_directory=self.drop_directory,
            xaxis_label = 'control', yaxis_label = 'cort', simulation=False, simtrials = 10000, convergence_test = False,
            graph_results = True, regionvarname = 'regionname', groupvarname = 'group', countvarname = 'normalizedcount')
        self.sstobj()

    def calculate_differences(self):
        self.df_stats = self.df_sum.groupby(['group', 'regionname', 'regionid'], as_index=False).agg(
            mean_rawcount=('normalizedcount', 'mean'),
            sem_rawcount=('normalizedcount', lambda x: np.std(x, ddof=1) / np.sqrt(len(x)))  # SEM = std / sqrt(n)
        )
        df_pivot = df_stats.pivot(index=['regionname', 'regionid'], columns='group', values='mean_rawcount').dropna()
        df_pivot['diff'] = np.abs(df_pivot['control'] - df_pivot['cort'])  # Adjust group names if needed
        df_pivot_filtered = df_pivot[df_pivot['diff'] > 0]
        top_regions = df_pivot_filtered.nlargest(20, 'diff').index
        df_stats_top = df_stats[df_stats.set_index(['regionname', 'regionid']).index.isin(top_regions)]
        colors = {"control": "blue", "cort": "red"} 
        g = sns.FacetGrid(df_stats_top, col="regionname", col_wrap=5, sharey=False, height=4)
                
        def barplot_with_errorbars(data, **kwargs):
            ax = plt.gca()
            sns.barplot(
                data=data, x="group", y="mean_rawcount", capsize=0.1, 
                palette=colors, edgecolor="black", linewidth=1.5, **kwargs
            )
            # Manually add error bars
            for i, group in enumerate(data["group"].unique()):
                subset = data[data["group"] == group]
                ax.errorbar(
                    x=i, y=subset["mean_rawcount"].values, 
                    yerr=subset["sem_rawcount"].values, fmt="none", 
                    ecolor="black", elinewidth=2, capsize=4, capthick=2
                )

            ax.set_xlabel("Group", fontsize=12)
            ax.set_ylabel("Average Cell Count", fontsize=12)
            # Set custom x-axis labels 
            for label in ax.get_xticklabels():
                label.set_fontsize(12)
                label.set_weight('bold')
            ax.set_xticks([0, 1])  # Ensure tick positions match the groups
            ax.set_xticklabels(["control", "cort"])

        g.map_dataframe(barplot_with_errorbars)

        for ax in g.axes.flatten():
            ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')

        for ax, title in zip(g.axes.flatten(), g.col_names):
            ax.set_title(f"{title}", fontsize=12, fontweight="bold")  # Bold and readable size

        plt.tight_layout()
        plt.savefig('largest_differences.jpg')
    
    def total_counts(self):
        df_total_cells = self.df.groupby(['suid', 'group'], as_index=False).agg({'rawcount': 'sum'})
        self.df_total_stats = df_total_cells.groupby('group', as_index=False).agg(
            mean_rawcount=('rawcount', 'mean'),
            sem_rawcount=('rawcount', lambda x: np.std(x, ddof=1) / np.sqrt(len(x)))  # SEM = std / sqrt(n)
        )

    def volcano(self):
        df_grouped = self.df.groupby(['suid', 'group', 'regionname'], as_index=False)[self.value].mean()

        fold_changes = []
        p_values = []
        for region in df_grouped['regionname'].unique():
            region_data = df_grouped[df_grouped['regionname'] == region]
            tmt_data = region_data[region_data['group'] == 'control'][self.value]
            water_data = region_data[region_data['group'] == 'cort'][self.value]
            fold_change = (tmt_data.mean() + 1)/ (water_data.mean()+1)
            fold_changes.append(fold_change)
            t_stat, p_value = stats.ttest_ind(tmt_data, water_data)
            p_values.append(p_value)

        volcano_df = pd.DataFrame({
            'regionname': df_grouped['regionname'].unique(),
            'fold_change': fold_changes,
            'p_value': p_values})
        volcano_df['neg_log_p_value'] = -np.log10(volcano_df['p_value'])
        volcano_df_sorted = volcano_df.sort_values(by=['p_value'], ascending=[True])
        self.top_10_regions = volcano_df_sorted.head(30)

        fig, ax = plt.subplots(figsize=(10, 6))
        sns.scatterplot(data=volcano_df, x='fold_change', y='neg_log_p_value', hue='neg_log_p_value', palette='coolwarm', edgecolor="black", ax=ax)
        ax.axhline(y=-np.log10(0.05), color='red', linestyle='--', label='p-value < 0.05')
        ax.axhline(y=-np.log10(0.1), color='green', linestyle='--', label='p-value < 0.1')
        ax.set_title("Volcano Plot: Fold Change vs Significance")
        ax.set_xlabel("Fold Change (control / cort)")
        ax.set_ylabel("-log10(p-value)")
       

        # for _, row in top_10_regions.iterrows():
        #     ax.annotate(
        #         row['regionname'], 
        #         (row['fold_change'], row['neg_log_p_value']),
        #         textcoords="offset points", 
        #         xytext=(0, 5),  # offset label by 5 points
        #         ha='center',
        #         fontsize=9
        #     )
        # ax.legend().remove()

        # inset_ax = inset_axes(ax, width="100%", height="100%", loc='center left', bbox_to_anchor=(0.05, 0.5, 0.1, 0.3), bbox_transform=ax.transAxes)
        # sns.scatterplot(data=volcano_df, x='fold_change', y='neg_log_p_value', hue='neg_log_p_value', palette='coolwarm', edgecolor="black", ax=inset_ax)

        # # inset_ax.set_xlim(-10, 10)
        # # inset_ax.set_ylim(-0.5, 4)  # Adjust as needed
        # inset_ax.axvline(x=1, color='black', linestyle='--')
        # inset_ax.set_title("") 
        # inset_ax.set_xlabel("Fold Change")
        # inset_ax.set_ylabel("-log10(p-value)")
        # inset_ax.legend().remove()
        # ax.legend().set_visible(False)
        #mark_inset(ax, inset_ax, loc1=2, loc2=4, fc="none", ec="0.5", ls="--")
        plt.tight_layout()
        plt.savefig('volcano.jpg')



if __name__=='__main__':
    df = pd.read_csv(r'C:\Users\listo\communal_registration_logcal_drop\rabies_experiment\control\df_tall.csv')
    df2 = pd.read_csv(r'C:\Users\listo\communal_registration_logcal_drop\rabies_experiment\experimental\df_tall.csv')
    df2['group'] = 'cort'
    df = pd.concat([df,df2])
    df['normalizedcount'] = df['normalizedcount']*100
    genobj = gen(df=df,value='normalizedcount')
    genobj.volcano()
    ipdb.set_trace()





# # Step 3: Plot the average total cell count per group with error bars (SEM)
# fig, ax = plt.subplots(figsize=(6, 6))

# # Plot the average raw cell count per group
# sns.barplot(data=df_stats, x="group", y="mean_rawcount", ax=ax, palette=colors, edgecolor="black", linewidth=1.5)

# # Add error bars using SEM
# for i, group in enumerate(df_stats["group"].unique()):
#     mean_value = df_stats[df_stats["group"] == group]["mean_rawcount"].values[0]
#     sem_value = df_stats[df_stats["group"] == group]["sem_rawcount"].values[0]
    
#     # Error bars (SEM)
#     ax.errorbar(x=i, y=mean_value, fmt="none", yerr=sem_value, ecolor="black", elinewidth=2, capsize=4, capthick=2)

# # Set title and labels
# ax.set_title("Average Total Cell Count per Group")
# ax.set_ylabel("Average Total Cell Count")
# ax.set_xlabel("Group")

# # Improve layout
# plt.tight_layout()

# plt.savefig('average_cells_per_group.jpg')




# # Assuming df is your DataFrame and it has columns 'regionname', 'suid' (subject ID), 'group', and 'rawcount'

# # Step 1: Subset the DataFrame by brain regions with specific substrings (Regions of Interest)
# df_sum_orig = df.groupby(['suid', 'group', 'regionname', 'regionid'], as_index=False).agg({'rawcount': 'sum'})
# regions_of_interest = ['raphe']
# df_subset = df_sum_orig[df_sum_orig['regionname'].str.contains('|'.join(regions_of_interest), case=False, na=False)]


# # Step 2: Group by subject ('suid') and group ('group'), and sum the 'rawcount' for each group
# df_sum = df_subset.groupby(['suid', 'group'])['rawcount'].sum().reset_index()

# # Step 3: Calculate the average and SEM of the summed counts across groups for the regions of interest
# df_avg_sem = df_sum.groupby('group').agg(
#     mean_sum=('rawcount', 'mean'),
#     sem_sum=('rawcount', lambda x: np.std(x, ddof=1) / np.sqrt(len(x)))
# ).reset_index()

# # Step 4: Identify TMT regions that are not part of the regions of interest
# df_non_roi = df_sum_orig[(df_sum_orig['group'] == 'tmt') & (~df_sum_orig['regionname'].str.contains('|'.join(regions_of_interest), case=False, na=False))]
# df_non_roi = df_non_roi[df_non_roi['rawcount'] > 0]

# # Step 5: Calculate the sum, average, and SEM of the summed counts for non-ROI TMT regions
# df_non_roi_sum = df_non_roi.groupby(['suid'])['rawcount'].mean().reset_index()

# # Now calculate the mean and SEM for non-ROI TMT regions
# non_roi_avg = df_non_roi_sum['rawcount'].mean()
# non_roi_sem = np.std(df_non_roi_sum['rawcount'], ddof=1) / np.sqrt(len(df_non_roi_sum))

# # Step 6: Add this extra bar to the plot
# df_avg_sem_non_roi = pd.DataFrame({
#     'group': ['Non-ROI TMT'],
#     'mean_sum': [non_roi_avg],
#     'sem_sum': [non_roi_sem]
# })

# # Append the non-ROI TMT data to the original df_avg_sem
# df_avg_sem = pd.concat([df_avg_sem, df_avg_sem_non_roi], ignore_index=True)


# # Step 1: Get unique brain regions
# unique_regions = df['regionname'].unique()
# p_values = []

# # Step 2: Perform t-tests for each region
# for region in unique_regions:
#     df_region = df[df['regionname'] == region]
    
#     # Separate TMT and Water groups
#     tmt_values = df_region[df_region['group'] == 'tmt']['rawcount']
#     water_values = df_region[df_region['group'] == 'water']['rawcount']
    
#     # Step 3: Perform t-test (use Mann-Whitney U test if needed)
#     if len(tmt_values) > 1 and len(water_values) > 1:
#         _, p = stats.ttest_ind(tmt_values, water_values, equal_var=False)
#     else:
#         p = np.nan  # Not enough data for a valid test

#     p_values.append({'regionname': region, 'p_value': p})

# # Step 4: Merge p-values into df
# df_pvals = pd.DataFrame(p_values)
# df = df.merge(df_pvals, on='regionname', how='left')

# # Step 1: Filter out regions of interest
# regions_of_interest = ['raphe']
# df_non_roi = df[~df['regionname'].str.contains('|'.join(regions_of_interest), case=False, na=False)]

# # Step 2: Keep only regions where p < 0.05
# df_significant = df_non_roi[df_non_roi['p_value'] < 0.05]

# # Step 3: Compute mean cell count per subject
# df_significant_mean = df_significant.groupby('suid')['rawcount'].mean().reset_index()

# # Step 4: Compute grand mean ± SEM
# mean_significant = df_significant_mean['rawcount'].mean()
# sem_significant = stats.sem(df_significant_mean['rawcount'])

# # Step 5: Append to df_avg_sem for plotting
# df_avg_sem = df_avg_sem.append({'group': 'Significant Non-mPFC', 
#                                 'mean_sum': mean_significant, 
#                                 'sem_sum': sem_significant}, 
#                                ignore_index=True)


# # Define a publication-quality color palette
# pub_colors = ['#D55E00',  # Muted Red (mPFC TMT)
#               '#0072B2',  # Muted Blue (mPFC Water)
#               '#CC6677',  # Soft Brick Red (Non-mPFC TMT)
#               '#882255']
# fig, ax = plt.subplots(figsize=(8, 6))

# # Plot bars using seaborn
# sns.barplot(data=df_avg_sem, x='group', y='mean_sum', capsize=0.1, palette=pub_colors, ax=ax)

# # Add error bars manually with Matplotlib
# x_positions = np.arange(len(df_avg_sem))  # Get x positions
# ax.errorbar(x=x_positions, 
#             y=df_avg_sem['mean_sum'], 
#             yerr=df_avg_sem['sem_sum'], 
#             fmt='none', 
#             ecolor='black', 
#             capsize=5, 
#             capthick=1, 
#             elinewidth=1)

# # Rename x-tick labels
# ax.set_xticks(range(len(df_avg_sem)))
# ax.set_xticklabels(['TMT Activated \n R Neurons', 'Water Activated \n R Neurons', 'TMT Activated \n Other Regions Neurons', 'Significant TMT Activated \n Other Regions Neurons'])

# # Add labels and title
# ax.set_ylabel('Mean Cell Count')

# # Show the plot
# plt.tight_layout()
# plt.savefig('Rcomp.jpg')
