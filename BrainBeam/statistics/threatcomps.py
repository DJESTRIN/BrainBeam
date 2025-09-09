#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: threatcomps.py
Description: A group of functions used for specific analyses regarding mPFC and its relevance in threat processing
Author: David Estrin
Date: 2025-09-08
Version: 1.0
"""
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import ttest_ind

def plot_mPFC_vs_brain(df, directory):
    # --- Define region categories ---
    mpfc_substrings = ["cingulate", "prelimbic", "infralimbic"]

    threat_substrings = [
        "amyg", "hypothal", "bed nucl", "periaqueduct",
        "collic", "thal", "sept", "cortex prelim",
        "cortex infralimb", "cingul", "insula",
        "stria term", "hippocamp", "entorhin",
        "olfact", "accumb", "haben", "raphe", "locus coer"
    ]

    canonical_threat = {
        "Amygdala": ["amyg"],
        "PAG": ["periaqueduct"],
        "Hypothalamus": ["hypothal"],
        "BNST": ["bed nucl"]
    }

    # Identify mPFC and threat-associated regions
    df['is_mPFC'] = df['regionname'].str.lower().apply(
        lambda x: any(sub in x for sub in mpfc_substrings)
    )
    df['is_threat'] = df['regionname'].str.lower().apply(
        lambda x: any(sub in x for sub in threat_substrings)
    )

    # --- Helpers ---
    def mean_sem(series):
        return series.mean(), series.sem()

    def subject_sum(df, mask):
        """Aggregate per subject (sum across regions), then compute mean ± SEM."""
        sub_df = df[mask & (df['group'] == 'tmt')]
        if sub_df.empty:
            return np.nan, np.nan
        sub_sum = sub_df.groupby('suid')['normalizedcount'].sum().reset_index()
        return mean_sem(sub_sum['normalizedcount'])

    def subject_region_avg(df, mask):
        """Aggregate per subject (average across regions), then compute mean ± SEM."""
        sub_df = df[mask & (df['group'] == 'tmt')]
        if sub_df.empty:
            return np.nan, np.nan
        subj_means = sub_df.groupby(['suid', 'regionname'])['normalizedcount'].mean().reset_index()
        subj_avg = subj_means.groupby('suid')['normalizedcount'].mean().reset_index()
        return mean_sem(subj_avg['normalizedcount'])

    # --- mPFC (sum of subregions) ---
    mpfc_mean, mpfc_sem = subject_sum(df, df['is_mPFC'])

    # --- All other regions (average across subregions) ---
    all_other_mean, all_other_sem = subject_region_avg(df, ~df['is_mPFC'])

    # --- Significant regions (vs water, average across subregions) ---
    sig_regions = []
    for region in df['regionname'].unique():
        region_data = df[df['regionname'] == region]
        tmt_vals = region_data[region_data['group'] == 'tmt']['normalizedcount']
        water_vals = region_data[region_data['group'] == 'water']['normalizedcount']
        if len(tmt_vals) > 1 and len(water_vals) > 1:
            _, p_val = ttest_ind(tmt_vals, water_vals, equal_var=False)
            if p_val < 0.05:
                sig_regions.append(region)
    sig_other_mean, sig_other_sem = subject_region_avg(df, df['regionname'].isin(sig_regions) & ~df['is_mPFC'])

    # --- Threat-associated regions (average across subregions) ---
    threat_mean, threat_sem = subject_region_avg(df, df['is_threat'])

    # --- Canonical threat regions (sum of subregions) ---
    canonical_means, canonical_sems = [], []
    for region_name, substrings in canonical_threat.items():
        mask = df['regionname'].str.lower().apply(lambda x: any(sub in x for sub in substrings))
        m, s = subject_sum(df, mask)
        canonical_means.append(m)
        canonical_sems.append(s)

    # --- Combine into plotting dataframe ---
    plot_data = pd.DataFrame({
        'Category': [
            'mPFC TMT',
            'All Other Regions TMT',
            'Significant Other Regions TMT',
            'Threat-Associated Regions TMT'
        ] + list(canonical_threat.keys()),
        'Mean': [
            mpfc_mean,
            all_other_mean,
            sig_other_mean,
            threat_mean
        ] + canonical_means,
        'SEM': [
            mpfc_sem,
            all_other_sem,
            sig_other_sem,
            threat_sem
        ] + canonical_sems
    })

    # Save plotting data as csv file
    csvfilename = os.path.join(directory,'mPFCvsBrain.csv')
    plot_data.to_csv(csvfilename)

    # --- Plot ---
    plt.figure(figsize=(12,6))
    plt.bar(
        x=np.arange(len(plot_data)),
        height=plot_data['Mean'],
        yerr=plot_data['SEM'],
        capsize=5,
        color=sns.color_palette("muted", len(plot_data)),
        edgecolor='black'
    )
    plt.xticks(np.arange(len(plot_data)), plot_data['Category'], rotation=30, ha='right')
    plt.ylabel('Normalized Cell Count')
    plt.title('mPFC vs Other Brain Regions: TMT Response')
    plt.tight_layout()
    plt.savefig('amygthreateval_with_canonical.jpg')
    plt.close()

    return plot_data