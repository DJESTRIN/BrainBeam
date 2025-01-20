#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: stability.py
Description: 
Author: David Estrin
Date: 2025-01-17
Version: 1.0
"""
from statsmodels.api import OLS as lm
from statsmodels.api import add_constant
from BrainBeam.statistics.datagenerator import generate_pseudo_data, increase_pseudo_stability
import ipdb
import numpy as np
import matplotlib.pyplot as plt
import tqdm

class slope_stability():
    def __init__(self, dataframe_oh, drop_directory, xaxis_label = 'CONTROL', yaxis_label = 'CORT', 
                 simulation=False, simtrials = 3000, convergence_test = False, graph_results = False):
        self.dataframe = dataframe_oh
        self.drop_directory = drop_directory
        self.xaxis_label = xaxis_label
        self.yaxis_label = yaxis_label
        self.simulation = simulation
        self.simtrials = simtrials
        self.convergence_test = convergence_test
        self.graph_results = graph_results
    
    def __call__(self):
        self.df_wide, self.X, self.y = self.tall_to_slope_wide()
        self.X, self.y = increase_pseudo_stability(X = self.X, y = self.y, percent_data = 0.7)
        self.slope_data, self.intercept_data = self.ols_slope()
        
        if self.simulation:
            self.subset_simulation()

    def tall_to_slope_wide(self):
        averages = self.dataframe.groupby(['BrainRegion', 'Group'])['NumberOfCells'].mean().reset_index()
        df_wide = averages.pivot(index='BrainRegion', columns='Group', values='NumberOfCells')
        df_wide = df_wide.reset_index()

        # Get X and Y values for simplicity
        X = df_wide[self.xaxis_label]  # Independent variable (X)
        X = add_constant(X)
        y = df_wide[self.yaxis_label]  # Dependent variable (Y)

        return df_wide, X, y

    def ols_slope(self, CI=0.95):
        # Fit the model with ordinary least squares and grab parameter data
        model = lm(self.y, self.X).fit()
        slope = model.params[1]
        intercept = model.params[0]

        # Calculate 95% CI for slope and intercept
        conf = model.conf_int(alpha=(1 - CI)) 
        slope_lo, slope_hi = conf[0][1], conf[1][1] 
        intercept_lo, intercept_hi = conf[0][0], conf[1][0] 

        # Return CI for slope
        intercept_data = [intercept_lo, intercept, intercept_hi]
        slope_data = [slope_lo, slope, slope_hi]
        return slope_data, intercept_data

    def plot_slope(self):
        self.X = self.X[self.xaxis_label]
        min_val = self.X.min()
        max_val = self.X.max()
        X_points = np.linspace(min_val, max_val, 51)

        plt.figure(figsize=(10, 6))
        plt.scatter(self.X,self.y)

        # Gather model information
        slope_lo, slope, slope_hi = self.slope_data
        intercept_lo, intercept, intercept_hi = self.intercept_data

        # Plot y = mx+b
        plt.plot(X_points, ((X_points*slope)+intercept), color='red')
        plt.plot(X_points, ((X_points*slope_lo)+intercept), color='red',linestyle='--')
        plt.plot(X_points, ((X_points*slope_hi)+intercept), color='red',linestyle='--')

        # Labels and title
        plt.xscale('log')
        plt.yscale('log')
        plt.xlabel(self.xaxis_label)
        plt.ylabel(self.yaxis_label)
        return

    def run_simulation(self, X_subset, y_subset):
        X_subset = add_constant(X_subset)
        model = lm(y_subset, X_subset).fit()
        try:
            slope = model.params[1]
        except:
            ipdb.set_trace()
        return slope

    def subset_simulation(self):
        """ 
        Create an np.nan array with num rows = len(X) and ncolumns = ntrials
        Pull out a random combination subset from original data where subset size is randomly taken from 3 to length of X
        Calculate the (1 - slope per trial)
        For matching rows that were pulled, put this calculated number into the nan array. 
        impute missing data
        k means and plot clusters ...
        """
        xy = np.array([self.X[self.xaxis_label], self.y]).T
        if self.convergence_test:
            ipdb.set_trace()
        
        else:
            simulated_slopes = []
            for k in tqdm.tqdm(range(self.simtrials)):
                numpulls = int(np.random.uniform(4, xy.shape[0]))
                indx = np.random.choice(xy.shape[0], numpulls, replace=False)
                subset = xy[indx]
                simulated_slopes.append(self.run_simulation(X_subset = subset[:,0], y_subset = subset[:,1]))
            ipdb.set_trace()

        

if __name__=='__main__':
    df = generate_pseudo_data()
    drop = r'C:\Users\listo\example_stability_data'
    slopeobj = slope_stability(dataframe_oh = df, drop_directory=drop, simulation = True)
    slopeobj()
    ipdb.set_trace()