#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: LSpredictions.py
Description: This script uses modeling to determine whether information about region salience improves predictability of stress vs control in rabies dataset. 
Author: David Estrin
Date: 2025-08-01
Version: 1.0
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import accuracy_score, f1_score, balanced_accuracy_score
from sklearn.metrics import confusion_matrix

class RegionClassifier:
    def __init__(
        self,
        df,
        test_size=0.3,
        random_state=42,
        l1_ratio=0.5,
        C=1.0,
        min_feature_sum=2):
        self.df = df.copy()
        self.test_size = test_size
        self.random_state = random_state
        self.l1_ratio = l1_ratio
        self.C = C
        self.min_feature_sum = min_feature_sum

    def prepare_data(self):
        # Shuffle
        self.df = self.df.sample(frac=1, random_state=self.random_state)

        # Combine region + laterality
        self.df["region_side"] = (
            self.df["regionname"].astype(str) + "_" +
            self.df["lateralization"].astype(str)
        )

        # Aggregate per subject
        pivot = (
            self.df
            .pivot_table(
                index=["suid", "group"],
                columns="region_side",
                values="rawcount",
                aggfunc="sum",
                fill_value=0
            )
            .reset_index()
        )

        # Split X / y
        self.y = pivot["group"]
        X = pivot.drop(columns=["group", "suid"])

        # Remove ultra-rare regions
        X = X.loc[:, X.sum(axis=0) >= self.min_feature_sum]
        self.X = X

        self.feature_names = X.columns.tolist()

        self.X_train, self.X_val, self.y_train, self.y_val = train_test_split(
            X,
            self.y,
            test_size=self.test_size,
            random_state=self.random_state,
            stratify=self.y
        )

        print(self.y_train.unique())
        # Normalize
        self.scaler = StandardScaler()
        self.X_train = self.scaler.fit_transform(self.X_train)
        self.X_val = self.scaler.transform(self.X_val)

    def fit(self):
        classes = np.unique(self.y_train)
        class_weights = compute_class_weight(
            class_weight="balanced",
            classes=classes,
            y=self.y_train
        )

        self.model = LogisticRegression(
            penalty="elasticnet",
            solver="saga",
            l1_ratio=self.l1_ratio,
            C=self.C,
            class_weight=dict(zip(classes, class_weights)),
            max_iter=5000
        )

        self.model.fit(self.X_train, self.y_train)

    def evaluate(self):
        y_pred = self.model.predict(self.X_val)
        pos_label = "cort" if "cort" in self.model.classes_ else self.model.classes_[-1]

        return {
            "accuracy": accuracy_score(self.y_val, y_pred),
            "balanced_accuracy": balanced_accuracy_score(self.y_val, y_pred),
            "f1": f1_score(self.y_val, y_pred, pos_label=pos_label)
        }

    def get_feature_weights(self, top_n=10):
        if top_n==-1:
            print('returning all weight values')
            df = pd.DataFrame({
            "region_side": self.feature_names,
            "beta": self.model.coef_[0]})
            return df
        
        df = pd.DataFrame({
            "region_side": self.feature_names,
            "beta": self.model.coef_[0]
        })
        df["abs_beta"] = df["beta"].abs()
        return df.sort_values("abs_beta", ascending=False).head(top_n)

    def cross_validated_performance(self, n_splits=5):
        skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=self.random_state)
        scores = {"accuracy": [], "balanced_accuracy": [], "f1": []}

        for train_idx, test_idx in skf.split(self.X, self.y):
            X_tr, X_te = self.X.iloc[train_idx], self.X.iloc[test_idx]
            y_tr, y_te = self.y.iloc[train_idx], self.y.iloc[test_idx]

            scaler = StandardScaler()
            X_tr = scaler.fit_transform(X_tr)
            X_te = scaler.transform(X_te)

            model = LogisticRegression(
                penalty="elasticnet",
                solver="saga",
                l1_ratio=self.l1_ratio,
                C=self.C,
                class_weight="balanced",
                max_iter=5000
            )

            model.fit(X_tr, y_tr)
            preds = model.predict(X_te)
            pos_label = "cort" if "cort" in model.classes_ else model.classes_[-1]

            scores["accuracy"].append(accuracy_score(y_te, preds))
            scores["balanced_accuracy"].append(balanced_accuracy_score(y_te, preds))
            scores["f1"].append(f1_score(y_te, preds, pos_label=pos_label))

        return {k: np.mean(v) for k, v in scores.items()}
    
    def confusion_long_df(self):
        """
        Return a long-format dataframe of TP, TN, FP, FN counts for the validation set.
        """
        # Get predicted labels
        y_pred = self.model.predict(self.X_val)

        # Confusion matrix: rows = true, cols = pred
        cm = confusion_matrix(self.y_val, y_pred, labels=np.unique(self.y_val))
        # Map to TP/TN/FP/FN for binary classification
        # Assuming labels: [control, cort]
        label_map = {label: i for i, label in enumerate(np.unique(self.y_val))}
        tn, fp, fn, tp = cm[0,0], cm[0,1], cm[1,0], cm[1,1]

        # Convert to long-format dataframe
        df_long = pd.DataFrame({
            'metric': ['TP', 'TN', 'FP', 'FN'],
            'value': [tp, tn, fp, fn]
        })
        return df_long

if __name__=='__main__':
    # User defined inputs
    dataframe_file = r'C:\Users\listo\communal_registration_logcal_drop\rabies_experiment\results2\dfsum.csv'
    rabiesdf = pd.read_csv(dataframe_file)
    model = RegionClassifier(df=rabiesdf)
    model.prepare_data()
    model.fit()
    metrics = model.evaluate()
    print("Validation metrics:")
    for k, v in metrics.items():
        print(f"{k}: {v:.3f}")
    weights = model.get_feature_weights(top_n=-1)
    weights.to_csv(r'C:\Users\listo\communal_registration_logcal_drop\rabies_experiment\results2\LogRegres_weights.csv')
    conf_df = model.confusion_long_df()
    conf_df.to_csv(r'C:\Users\listo\communal_registration_logcal_drop\rabies_experiment\results2\confusionmatrix.csv')

    