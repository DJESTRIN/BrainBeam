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
import ipdb

def plot_mPFC_vs_brain(df, counttype, directory):
    df = df.copy()
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
    "Hypothalamus": ["hypothal"], 
    "BNST": ["bed nucl"],
    "PAG": ["periaqueduct"],
    "Superior Colliculus": ["collic"],
    "Thalamus": ["thalamus"], 
    "Septum": ["sept"],
    "Insula": ["insula"],
    "Stria Terminalis": ["stria term"],
    "Hippocampus": ["hippocamp"],
    "Entorhinal Cortex": ["entorhin"],
    "Olfactory Regions": ["olfact"],
    "Nucleus Accumbens": ["accumb"],
    "Habenula": ["haben"],
    "Raphe Nuclei": ["raphe"],
    "Locus Coeruleus": ["locus coer"],
    "Ventral Tegmental Area": ["ventral tegmental", "VTA"],
    "Parabrachial Nucleus": ["parabrach"]}

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
        sub_sum = sub_df.groupby('suid')[counttype].sum().reset_index()
        return mean_sem(sub_sum[counttype])

    def subject_region_avg(df, mask):
        """Aggregate per subject (average across regions), then compute mean ± SEM."""
        sub_df = df[mask & (df['group'] == 'tmt')]
        if sub_df.empty:
            return np.nan, np.nan
        subj_means = sub_df.groupby(['suid', 'regionname'])[counttype].mean().reset_index()
        subj_avg = subj_means.groupby('suid')[counttype].mean().reset_index()
        return mean_sem(subj_avg[counttype])

    # --- mPFC (sum of subregions) ---
    mpfc_mean, mpfc_sem = subject_sum(df, df['is_mPFC'])

    # --- All other regions (average across subregions) ---
    all_other_mean, all_other_sem = subject_region_avg(df, ~df['is_mPFC'])

    # --- Significant regions (vs water, average across subregions) ---
    sig_regions = []
    for region in df['regionname'].unique():
        region_data = df[df['regionname'] == region]
        tmt_vals = region_data[region_data['group'] == 'tmt'][counttype]
        water_vals = region_data[region_data['group'] == 'water'][counttype]
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

    # --- Build canonical-only dataframe ---
    canonical_df = pd.DataFrame({
        'Region': list(canonical_threat.keys()),
        'Mean': canonical_means,
        'SEM': canonical_sems
    })

    # Add mPFC to this table
    mpfc_row = pd.DataFrame({
        'Region': ['mPFC'],
        'Mean': [mpfc_mean],
        'SEM': [mpfc_sem]
    })

    canonical_with_mpfc = pd.concat([mpfc_row, canonical_df], ignore_index=True)


    # ============================
    #  Plot 1: mPFC vs Threat-Associated Average
    # ============================

    plot1_df = pd.DataFrame({
        'Category': ['mPFC', 'Threat-Associated (Avg)'],
        'Mean': [mpfc_mean, threat_mean],
        'SEM': [mpfc_sem, threat_sem]
    })

    # Sort high → low mean
    plot1_df = plot1_df.sort_values('Mean', ascending=False)

    plt.figure(figsize=(6,5))
    plt.bar(
        x=np.arange(len(plot1_df)),
        height=plot1_df['Mean'],
        yerr=plot1_df['SEM'],
        capsize=5,
        color=sns.color_palette("muted", len(plot1_df)),
        edgecolor='black'
    )
    plt.xticks(np.arange(len(plot1_df)), plot1_df['Category'], rotation=20, ha='right')
    plt.ylabel('Normalized Cell Count')
    plt.title('TMT Activation: mPFC vs Threat-Associated Average (Rank Ordered)')
    plt.tight_layout()
    plt.savefig(os.path.join(directory, 'Plot1_mPFC_vs_ThreatAverage.jpg'))
    plt.close()


    # ============================
    #  Plot 2: mPFC vs Canonical Threat Regions (rank ordered)
    # ============================

    # Sort high → low mean
    plot2_df = canonical_with_mpfc.sort_values('Mean', ascending=False)

    plt.figure(figsize=(10,6))
    plt.bar(
        x=np.arange(len(plot2_df)),
        height=plot2_df['Mean'],
        yerr=plot2_df['SEM'],
        capsize=5,
        color=sns.color_palette("muted", len(plot2_df)),
        edgecolor='black'
    )
    plt.xticks(np.arange(len(plot2_df)), plot2_df['Region'], rotation=30, ha='right')
    plt.ylabel('Normalized Cell Count')
    plt.title('TMT Activation: mPFC vs Individual Threat-Associated Regions (Rank Ordered)')
    plt.tight_layout()
    plt.savefig(os.path.join(directory, 'Plot2_mPFC_vs_CanonicalThreatRegions.jpg'))
    plt.close()


    return 