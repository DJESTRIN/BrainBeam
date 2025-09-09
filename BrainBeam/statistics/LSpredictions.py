#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: LSpredictions.py
Description: This script uses modeling to determine whether information about region salience improves predictability of stress vs control in rabies dataset. 
Author: David Estrin
Date: 2025-08-01
Version: 1.0
"""
import json
import pandas as pd
import os
import ipdb
import statsmodels.formula.api as smf
import statsmodels.formula.api as smf
import itertools
import tqdm
import statsmodels.formula.api as smf
import scipy.stats as stats
import itertools
import tqdm
import pandas as pd
import statsmodels.api as sm
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report
import pandas as pd
import numpy as np
from sklearn.model_selection import GridSearchCV, cross_val_predict
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report
import numpy as np
from sklearn.model_selection import StratifiedKFold, GridSearchCV, cross_val_predict
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report
import numpy as np
import ipdb
from itertools import combinations
from sklearn.metrics import f1_score
import matplotlib.pyplot as plt
from scipy.special import expit  # sigmoid function
import math





"""
How can we determine if there is a link between changes in mPFC connectiivty and whether a region encodes TMT, water or vanilla.

Variables of interest:
t statistics
normalized cell counts
stability values

Types of analyses:
linear (or nonlinear) model group ~ rabies_region_value vs group ~ rabies_region_value*salience_value(s)
    which model performs better?
    A model with one brain region at a time makes better sense because the ratio of samples to hyperparamters



"""

def aicc(model):
    n = model.nobs
    k = model.df_model + 1
    return model.aic + (2 * k * (k + 1)) / (n - k - 1)


class linearmodeling():
    def __init__(self,talldf,summarydf,**args):
        self.talldf = talldf
        self.summarydf = summarydf
    
    def __call__(self):
        self.merge_data()
        self.logmodeling_wide_elasticnet()
        ipdb.set_trace()
    
    def merge_data(self):
        self.merged_df = pd.merge( self.talldf,  # your long dataframe
            self.summarydf ,  # your summary dataframe
            on=['regionname', 'lateralization'],
            how='left',
            suffixes=('_rabies', '_salience')
            )
        self.merged_df['group_rabies_num'] = self.merged_df['group_rabies'].map({'control': 0, 'cort': 1})

    def logmodeling_wide_elasticnet(self):
        # 1. Pivot to wide format: rows = suid, columns = regions
        df_wide = (
            self.talldf
            .assign(region_lat=lambda d: d['regionname'] + '_' + d['lateralization'])
            .pivot_table(
                index='suid',
                columns='region_lat',
                values='normalizedcount',
                aggfunc='mean'
            )
            .fillna(0)
        )

        # 2. Merge group label
        group_labels = self.merged_df[['suid', 'group_rabies_num']].drop_duplicates()
        df_wide = df_wide.merge(group_labels, on='suid', how='left')

        # 3. Split features and target
        X = df_wide.drop(columns=['group_rabies_num', 'suid'])
        y = df_wide['group_rabies_num']

        # 4. ElasticNet regularized logistic regression pipeline
        pipe = Pipeline([
            ('scaler', StandardScaler()),
            ('clf', LogisticRegression(penalty='elasticnet', solver='saga', max_iter=5000))
        ])

        # 5. Define stratified k-fold cross-validation
        stratified_cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

        # 6. Use GridSearchCV to tune C (inverse of regularization strength) and l1_ratio with stratified CV
        param_grid = {
            'clf__C': np.logspace(-4, 2, 10),  # test range from strong to weak regularization
            'clf__l1_ratio': [0.1, 0.5, 0.9],  # amount of L1 vs L2
        }

        search = GridSearchCV(pipe, param_grid, cv=stratified_cv, scoring='accuracy', verbose=1, n_jobs=-1)
        search.fit(X, y)

        # 7. Save best model and CV results
        self.model_results = search.best_estimator_
        self.model_cv_results = search.cv_results_

        self.plot_logistic_sigmoid(X, y)


        print(f"Best parameters: {search.best_params_}")

        # 8. Cross-validated predictions using the best estimator with stratified folds
        y_pred_cv = cross_val_predict(self.model_results, X, y, cv=stratified_cv)

        print("Classification Report (Cross-validated predictions):")
        print(classification_report(y, y_pred_cv))

        # Optional: print non-zero coefficients from the best estimator fit on full data
        clf_final = self.model_results.named_steps['clf']
        coefs = clf_final.coef_[0]
        region_names = X.columns

        # Create list of (region, coef) and sort by absolute coef descending
        sorted_coefs = sorted(zip(region_names, coefs), key=lambda x: abs(x[1]), reverse=True)

        print("\nTop 28 coefficients by absolute value:")
        for name, coef in sorted_coefs[:28]:
            print(f"{name}: {coef:.4f}")

        # Step 1: get coefs and regions, remove zeros
        clf_final = self.model_results.named_steps['clf']
        region_names = self.model_results.named_steps['scaler'].feature_names_in_  # or however you get columns
        coefs = clf_final.coef_[0]

        # Filter out zero coefficients
        nonzero = [(r, c) for r, c in zip(region_names, coefs) if c != 0]
        if len(nonzero) == 0:
            print("No non-zero coefficients found.")
            return

        # Sort by absolute coefficient descending
        sorted_coefs = sorted(nonzero, key=lambda x: abs(x[1]), reverse=True)

        total_regions = len(sorted_coefs)

        # 28 corresponds approx 5%, so multiples of 28 until 50%
        max_count = math.floor(total_regions * 0.5)
        step = 28
        thresholds = list(range(28, 113, 28))

        def categorize_region(region_name):
            region_name_lower = region_name.lower()
            if 'thala' in region_name_lower:
                return 'Thalamus'
            elif 'olfact' in region_name_lower:
                return 'Olfactory bulb'
            elif 'somato' in region_name_lower:
                return 'Primary Somatosnesory Cortex'
            else:
                # Heuristic for PFC:
                # Common PFC region substrings: 'pl', 'ila', 'aca', 'm2', 'm1', 'orb', 'cing' etc.
                # You can extend this list as needed
                pfc_keywords = ['prelim', 'infralim', 'anterior cingulate', 'orbit', 'insula', 'cing', 'm2', 'm1', 'mpfc']
                if any(k in region_name_lower for k in pfc_keywords):
                    return 'PFC'
                else:
                    return 'Other'

        n_plots = len(thresholds)
        fig, axes = plt.subplots(1, n_plots, figsize=(4*n_plots, 4))

        if n_plots == 1:
            axes = [axes]

        for ax, n_top in zip(axes, thresholds):
            top_regions = sorted_coefs[:n_top]
            categories = [categorize_region(r) for r, _ in top_regions]
            counts = pd.Series(categories).value_counts()

            ax.pie(counts, labels=counts.index, autopct='%1.0f%%', startangle=90)
            ax.set_title(f'Top {n_top} regions\n(~{n_top/28*5:.1f}%)')
        
        plt.tight_layout()
        plt.savefig('piecharts.jpg')

        category_colors = {
            'PFC': '#b586e9',          # blue
            'Thalamus': '#f4a582',     # orange
            'Primary Somatosnesory Cortex':'#cbaacb' ,
            'Olfactory bulb': '#72b6a1',  # green
            'Other': '#a8a8a8',        # red
        }

        fig, axes = plt.subplots(1, n_plots, figsize=(4*n_plots, 4))

        if n_plots == 1:
            axes = [axes]

        for ax, n_top in zip(axes, thresholds):
            top_regions = sorted_coefs[:n_top]
            categories = [categorize_region(r) for r, _ in top_regions]
            counts = pd.Series(categories).value_counts()

            # Get colors in the order of counts.index (categories in this pie)
            colors = [category_colors.get(cat, '#7f7f7f') for cat in counts.index]  # default gray

            ax.pie(counts, startangle=90, colors=colors)
            ax.set_title(f'Top {n_top} regions\n(~{n_top/28*5:.1f}%)')
            ax.axis('equal')  # keep pies circular

        plt.tight_layout()
        plt.savefig('piecharts_colored.jpg')

        ipdb.set_trace()
    
    def permutation_test_top_regions(self, n_permutations=1000, top_percent=0.10):
        """
        Tests whether the top N% coefficients from the logistic regression
        are significantly higher than expected by chance using permutation testing.
        """
        # --- Step 1: Prepare the data like in your original method ---
        df_wide = (
            self.talldf
            .assign(region_lat=lambda d: d['regionname'] + '_' + d['lateralization'])
            .pivot_table(
                index='suid',
                columns='region_lat',
                values='normalizedcount',
                aggfunc='mean'
            )
            .fillna(0)
        )

        group_labels = self.merged_df[['suid', 'group_rabies_num']].drop_duplicates()
        df_wide = df_wide.merge(group_labels, on='suid', how='left')

        X = df_wide.drop(columns=['group_rabies_num', 'suid'])
        y = df_wide['group_rabies_num']

        # --- Step 2: Fit the real model ---
        pipe = Pipeline([
            ('scaler', StandardScaler()),
            ('clf', LogisticRegression(
                penalty='elasticnet', solver='saga',
                l1_ratio=0.5, C=1.0,  # Could use best from GridSearchCV
                max_iter=5000
            ))
        ])
        pipe.fit(X, y)
        coefs_real = pipe.named_steps['clf'].coef_[0]

        # Get threshold for top X% by absolute coefficient
        n_top = 28
        sorted_idx_real = np.argsort(np.abs(coefs_real))[::-1]
        top_real_regions = X.columns[sorted_idx_real[:n_top]]
        top_real_magnitudes = np.abs(coefs_real[sorted_idx_real[:n_top]])

        # --- Step 3: Permutation loop ---
        rng = np.random.default_rng(42)
        max_null_distrib = []

        for i in tqdm.tqdm(range(n_permutations)):
            y_perm = rng.permutation(y)

            pipe.fit(X, y_perm)
            coefs_perm = np.abs(pipe.named_steps['clf'].coef_[0])
            top_perm = np.sort(coefs_perm)[-n_top:]  # top N absolute coefs
            max_null_distrib.append(np.mean(top_perm))

        max_null_distrib = np.array(max_null_distrib)

        # --- Step 4: p-value calculation ---
        real_mean_top = np.mean(top_real_magnitudes)
        p_value = np.mean(max_null_distrib >= real_mean_top)

        print(f"\nPermutation test results ({n_permutations} shuffles):")
        print(f"Mean magnitude of real top {top_percent*100:.0f}%: {real_mean_top:.4f}")
        print(f"Null mean ± SD: {max_null_distrib.mean():.4f} ± {max_null_distrib.std():.4f}")
        print(f"P-value: {p_value:.4f}")
        print(f"Top regions: {list(top_real_regions)}")

        # --- Step 5: Optional visualization ---
        import matplotlib.pyplot as plt
        plt.hist(max_null_distrib, bins=30, alpha=0.7, label='Null (permuted)')
        plt.axvline(real_mean_top, color='red', linestyle='--', label='Observed')
        plt.xlabel(f"Mean magnitude of top {top_percent*100:.0f}% coefficients")
        plt.ylabel("Frequency")
        plt.title("Permutation test for top coefficient magnitudes")
        plt.legend()
        plt.savefig('permutation.jpg')
        ipdb.set_trace()

    def plot_logistic_sigmoid(self, X, y, csv_prefix='logistic_sigmoid'):
        clf_final = self.model_results.named_steps['clf']
        scaler = self.model_results.named_steps['scaler']

        # Standardize X
        X_scaled = scaler.transform(X)

        # Compute logits and probabilities
        logit = np.dot(X_scaled, clf_final.coef_[0]) + clf_final.intercept_[0]
        prob = expit(logit)

        # Sort logits for smooth line
        sort_idx = np.argsort(logit)
        logit_sorted = logit[sort_idx]
        prob_sorted = prob[sort_idx]

        # Plot
        plt.figure(figsize=(8, 6))
        plt.scatter(logit, y, label='True labels', alpha=0.5)
        plt.plot(logit_sorted, prob_sorted, color='red', label='Sigmoid fit')
        plt.xlabel("Logit (Linear combination of features)")
        plt.ylabel("Probability")
        plt.title("Logistic Regression S-curve (projected to 1D)")
        plt.legend()
        plt.grid(True)
        plt.savefig(f'{csv_prefix}.jpg')
        plt.close()

        # Prepare DataFrame for CSV
        # Save both points (logit vs y) and smooth line (logit_sorted vs prob_sorted)
        df_points = pd.DataFrame({'logit': logit, 'true_label': y})
        df_line = pd.DataFrame({'logit_sorted': logit_sorted, 'prob_sorted': prob_sorted})

        # Save two separate CSVs or combined CSV with an indicator column
        df_points.to_csv(f'{csv_prefix}_points.csv', index=False)
        df_line.to_csv(f'{csv_prefix}_curve.csv', index=False)

    def logmodeling_wide_elasticnet_sal(self):
        # 1. Pivot rabies counts to wide format: rows = suid, columns = regions with lateralization
        df_rabies = (
            self.merged_df
            .assign(region_lat=lambda d: d['regionname'] + '_' + d['lateralization'])
            .pivot_table(
                index='suid',
                columns='region_lat',
                values='normalizedcount_rabies',
                aggfunc='mean'
            )
            .fillna(0)
        )

        # 2. Pivot salience counts to wide format: rows = suid, columns = regions with lateralization
        # Assumes normalizedcount_salience is measured per mouse and region (if group-level, see note below)
        # 2. Pivot salience counts to wide format with odor groups
        df_salience = (
            self.merged_df
            .assign(region_lat=lambda d: d['regionname'] + '_' + d['lateralization'])
            .pivot_table(
                index='suid',
                columns=['region_lat', 'group_salience'],  # multi-index columns
                values='normalizedcount_salience',
                aggfunc='mean'
            )
            .fillna(0)
        )

        # Flatten columns to single level
        df_salience.columns = [f"{region}_{group}_salience" for region, group in df_salience.columns]

        # 3. Combine rabies and salience features
        df_features = pd.concat([df_rabies, df_salience], axis=1).fillna(0)

        # 4. Merge group label
        group_labels = self.merged_df[['suid', 'group_rabies_num']].drop_duplicates()
        df_wide = df_features.merge(group_labels, left_index=True, right_on='suid', how='left')

        # 5. Prepare feature matrix X and target y
        X = df_wide.drop(columns=['group_rabies_num', 'suid'])
        y = df_wide['group_rabies_num']

        # 6. ElasticNet regularized logistic regression pipeline
        pipe = Pipeline([
            ('scaler', StandardScaler()),
            ('clf', LogisticRegression(penalty='elasticnet', solver='saga', max_iter=5000))
        ])

        # 7. Stratified k-fold cross-validation
        stratified_cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

        # 8. Grid search on regularization parameters
        param_grid = {
            'clf__C': np.logspace(-4, 2, 10),  # from strong to weak regularization
            'clf__l1_ratio': [0.1, 0.5, 0.9],  # L1 vs L2 balance
        }

        search = GridSearchCV(pipe, param_grid, cv=stratified_cv, scoring='accuracy', verbose=1, n_jobs=-1)
        search.fit(X, y)

        # 9. Save best estimator and cv results
        self.model_results = search.best_estimator_
        self.model_cv_results = search.cv_results_

        print(f"Best parameters: {search.best_params_}")

        # 10. Cross-validated predictions on full data
        y_pred_cv = cross_val_predict(self.model_results, X, y, cv=stratified_cv)

        print("Classification Report (Cross-validated predictions):")
        print(classification_report(y, y_pred_cv))

        ipdb.set_trace()

    def logmodeling_wide_elasticnet_sal_combinations(self):
        from itertools import combinations
        from sklearn.metrics import f1_score

        # 1. Pivot rabies counts to wide format
        df_rabies = (
            self.merged_df
            .assign(region_lat=lambda d: d['regionname'] + '_' + d['lateralization'])
            .pivot_table(
                index='suid',
                columns='region_lat',
                values='normalizedcount_rabies',
                aggfunc='mean'
            )
            .fillna(0)
        )

        # 2. Identify unique salience groups
        salience_groups = self.merged_df['group_salience'].dropna().unique()
        salience_groups = [str(g) for g in salience_groups]

        # 3. Pivot salience counts to wide format with group_salience and region_lat
        df_salience_all = (
            self.merged_df
            .assign(region_lat=lambda d: d['regionname'] + '_' + d['lateralization'])
            .pivot_table(
                index='suid',
                columns=['region_lat', 'group_salience'],
                values='normalizedcount_salience',
                aggfunc='mean'
            )
            .fillna(0)
        )
        df_salience_all.columns = [f"{region}_{group}_salience" for region, group in df_salience_all.columns]

        # 4. Group labels
        group_labels = self.merged_df[['suid', 'group_rabies_num']].drop_duplicates()

        results = []

        # 0. BASELINE model (no salience)
        df_wide_base = df_rabies.merge(group_labels, left_index=True, right_on='suid', how='left')
        X_base = df_wide_base.drop(columns=['group_rabies_num', 'suid'])
        y_base = df_wide_base['group_rabies_num']

        pipe = Pipeline([
            ('scaler', StandardScaler()),
            ('clf', LogisticRegression(penalty='elasticnet', solver='saga', max_iter=5000))
        ])
        stratified_cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        param_grid = {
            'clf__C': np.logspace(-4, 2, 10),
            'clf__l1_ratio': [0.1, 0.5, 0.9],
        }

        search = GridSearchCV(pipe, param_grid, cv=stratified_cv, scoring='accuracy', verbose=0, n_jobs=-1)
        search.fit(X_base, y_base)
        best_model = search.best_estimator_
        y_pred_base = cross_val_predict(best_model, X_base, y_base, cv=stratified_cv)
        f1_base = f1_score(y_base, y_pred_base)

        results.append({
            'Salience Groups': 'None (Baseline)',
            'Best Params': search.best_params_,
            'F1 Score': f1_base
        })

        # 5. All non-empty combinations of salience groups
        for r in range(1, len(salience_groups) + 1):
            for combo in combinations(salience_groups, r):
                combo = list(combo)
                salience_cols = [col for col in df_salience_all.columns if any(f"_{g}_salience" in col for g in combo)]

                df_features = pd.concat([df_rabies, df_salience_all[salience_cols]], axis=1).fillna(0)
                df_wide = df_features.merge(group_labels, left_index=True, right_on='suid', how='left')

                X = df_wide.drop(columns=['group_rabies_num', 'suid'])
                y = df_wide['group_rabies_num']

                search = GridSearchCV(pipe, param_grid, cv=stratified_cv, scoring='accuracy', verbose=0, n_jobs=-1)
                search.fit(X, y)
                best_model = search.best_estimator_
                y_pred_cv = cross_val_predict(best_model, X, y, cv=stratified_cv)
                f1 = f1_score(y, y_pred_cv)

                results.append({
                    'Salience Groups': ", ".join(combo),
                    'Best Params': search.best_params_,
                    'F1 Score': f1
                })

        # Print all results
        print("\nF1 Scores for Salience Group Combinations (including baseline):\n")
        print(f"{'Salience Groups':30s} | {'F1 Score':8s} | {'Best Params'}")
        print("-" * 80)
        for res in sorted(results, key=lambda x: -x['F1 Score']):
            print(f"{res['Salience Groups']:30s} | {res['F1 Score']:.3f}   | {res['Best Params']}")

        ipdb.set_trace()

        ipdb.set_trace()

    def logmodeling_wide_elasticnet_sal_combinations2(self):
        from itertools import combinations
        from sklearn.metrics import f1_score

        # 1. Pivot rabies counts to wide format
        df_rabies = (
            self.merged_df
            .assign(region_lat=lambda d: d['regionname'] + '_' + d['lateralization'])
            .pivot_table(
                index='suid',
                columns='region_lat',
                values='normalizedcount_rabies',
                aggfunc='mean'
            )
            .fillna(0)
        )

        # 2. Identify unique salience groups
        salience_groups = self.merged_df['group_salience'].dropna().unique()
        salience_groups = [str(g) for g in salience_groups]

        # 3. Pivot salience counts to wide format (group-level salience t-values)
        df_salience_group = (
            self.merged_df
            .assign(region_lat=lambda d: d['regionname'] + '_' + d['lateralization'])
            .groupby(['region_lat', 'group_salience'])['normalizedcount_salience']
            .mean()
            .unstack()
            .fillna(0)
        )
        # Now: rows = region_lat, columns = group_salience

        # 4. Group labels
        group_labels = self.merged_df[['suid', 'group_rabies_num']].drop_duplicates()

        results = []

        # 0. BASELINE model (no salience weighting)
        df_wide_base = df_rabies.merge(group_labels, left_index=True, right_on='suid', how='left')
        X_base = df_wide_base.drop(columns=['group_rabies_num', 'suid'])
        y_base = df_wide_base['group_rabies_num']

        pipe = Pipeline([
            ('scaler', StandardScaler()),
            ('clf', LogisticRegression(penalty='elasticnet', solver='saga', max_iter=5000))
        ])
        stratified_cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        param_grid = {
            'clf__C': np.logspace(-4, 2, 10),
            'clf__l1_ratio': [0.1, 0.5, 0.9],
        }

        search = GridSearchCV(pipe, param_grid, cv=stratified_cv, scoring='accuracy', verbose=0, n_jobs=-1)
        search.fit(X_base, y_base)
        best_model = search.best_estimator_
        y_pred_base = cross_val_predict(best_model, X_base, y_base, cv=stratified_cv)
        f1_base = f1_score(y_base, y_pred_base)

        results.append({
            'Salience Groups': 'None (Baseline)',
            'Best Params': search.best_params_,
            'F1 Score': f1_base
        })

        # 5. Loop over salience group combinations
        for r in range(1, len(salience_groups) + 1):
            for combo in combinations(salience_groups, r):
                combo = list(combo)

                # Average salience t-values across selected group(s)
                salience_weights = df_salience_group[combo].prod(axis=1)

                # Only keep rabies regions that overlap with salience weights
                common_regions = df_rabies.columns.intersection(salience_weights.index)

                # Apply salience weighting to rabies features
                df_weighted = df_rabies[common_regions] * salience_weights[common_regions]

                # Combine weighted features with group labels
                df_wide = df_weighted.merge(group_labels, left_index=True, right_on='suid', how='left')
                X = df_wide.drop(columns=['group_rabies_num', 'suid'])
                y = df_wide['group_rabies_num']

                # Fit and evaluate
                search = GridSearchCV(pipe, param_grid, cv=stratified_cv, scoring='accuracy', verbose=0, n_jobs=-1)
                search.fit(X, y)
                best_model = search.best_estimator_
                y_pred_cv = cross_val_predict(best_model, X, y, cv=stratified_cv)
                f1 = f1_score(y, y_pred_cv)

                results.append({
                    'Salience Groups': ", ".join(combo),
                    'Best Params': search.best_params_,
                    'F1 Score': f1
                })

        # Print all results
        print("\nF1 Scores for Salience Group Combinations (Weighted by Salience, Option 4):\n")
        print(f"{'Salience Groups':30s} | {'F1 Score':8s} | {'Best Params'}")
        print("-" * 80)
        for res in sorted(results, key=lambda x: -x['F1 Score']):
            print(f"{res['Salience Groups']:30s} | {res['F1 Score']:.3f}   | {res['Best Params']}")





    def modeling(self):
        salience_groups = self.merged_df['group_salience'].unique().tolist()

        # One-hot encode group_salience for each group
        for group in salience_groups:
            col_name = f'salience_{group}'
            self.merged_df[col_name] = (self.merged_df['group_salience'] == group).astype(int)

        results = []

        # Loop over each regionname
        for region in tqdm.tqdm(self.merged_df['regionname'].unique()):
            df_region = self.merged_df[self.merged_df['regionname'] == region]

            # Skip regions with insufficient variability
            if df_region['normalizedcount_rabies'].nunique() <= 1:
                continue

            # Base model (no salience groups)
            base_formula = "group_rabies_num ~ normalizedcount_rabies"
            try:
                base_model = smf.ols(formula=base_formula, data=df_region).fit()
                base_aic = base_model.aic
                base_llf = base_model.llf
                base_df = base_model.df_model

                results.append({
                    'regionname': region,
                    'groups_added': (),
                    'aic': base_aic,
                    'formula': base_formula,
                    'lr_stat': None,
                    'lr_df': None,
                    'lr_pvalue': None
                })

            except Exception:
                continue

            # Try all combinations of salience groups
            for r in range(1, len(salience_groups) + 1):
                for combo in itertools.combinations(salience_groups, r):
                    try:
                        salience_terms = ' + '.join([f'salience_{g}' for g in combo])
                        full_formula = f"group_rabies_num ~ normalizedcount_rabies + {salience_terms}"
                        model = smf.ols(formula=full_formula, data=df_region).fit()

                        lr_stat = 2 * (model.llf - base_llf)
                        lr_df = model.df_model - base_df
                        lr_pvalue = stats.chi2.sf(lr_stat, df=lr_df)

                        results.append({
                            'regionname': region,
                            'groups_added': combo,
                            'aic': model.aic,
                            'formula': full_formula,
                            'lr_stat': lr_stat,
                            'lr_df': lr_df,
                            'lr_pvalue': lr_pvalue
                        })

                    except Exception:
                        continue

        # Save results
        self.results = pd.DataFrame(results).sort_values(['regionname', 'aic'])

        significant = self.results[
            (self.results['lr_pvalue'] < 0.05) & 
            (self.results['lr_stat'].notnull())
        ]
        ipdb.set_trace()


if __name__=='__main__':
    # User defined inputs
    rabiesrestricteddataframe = r'C:\Users\listo\communal_registration_logcal_drop\rabies_experiment\results\restrictedrabiesdata.csv'
    rabiesdf = pd.read_csv(rabiesrestricteddataframe)

    # User defined inputs
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
    restrict_the_atlas = False

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
    saliencedf = pd.concat([df1,df2,df3])
    saliencedf['normalizedcount'] = saliencedf['normalizedcount']*100

    saliencedf_summary=saliencedf.groupby(['group', 'regionname','lateralization'], as_index=False)['normalizedcount'].mean()
    mymodel = linearmodeling(talldf=rabiesdf,summarydf=saliencedf_summary)
    mymodel()