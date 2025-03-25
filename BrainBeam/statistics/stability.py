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
import argparse
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import pandas as pd
import tqdm

class slope_stability():
    def __init__(self, dataframe_oh, drop_directory, xaxis_label = 'CONTROL', yaxis_label = 'CORT', 
                 simulation=False, simtrials = 10000, convergence_test = False, graph_results = False,
                 regionvarname = 'BrainRegion', groupvarname = 'Group', countvarname = 'NumberOfCells'):
        self.dataframe = dataframe_oh
        self.drop_directory = drop_directory
        self.xaxis_label = xaxis_label
        self.yaxis_label = yaxis_label
        self.simulation = simulation
        self.simtrials = simtrials
        self.convergence_test = convergence_test
        self.graph_results = graph_results

        # Variable names
        self.regionvarname = regionvarname
        self.groupvarname = groupvarname
        self.countvarname = countvarname
    
    def __call__(self):
        self.df_wide, self.X, self.y = self.tall_to_slope_wide()
        # self.X, self.y = increase_pseudo_stability(X = self.X, y = self.y, percent_data = 0.7)
        self.slope_data, self.intercept_data = self.ols_slope()
        
        if self.graph_results:
            self.plot_slope()
        
        if self.simulation:
            self.subset_simulation()

    def tall_to_slope_wide(self):
        averages = self.dataframe.groupby([ self.regionvarname , self.groupvarname])[self.countvarname].mean().reset_index()
        df_wide = averages.pivot(index= self.regionvarname , columns=self.groupvarname, values=self.countvarname)
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

    def plot_slope(self,label_oh='stability_general.jpg'):
        Xoh = self.X[self.xaxis_label]
        min_val = Xoh.min()
        max_val = Xoh.max()
        X_points = np.logspace(np.log10(min_val+0.01), np.log10(max_val), 1000)
        sns.set(style="whitegrid", context="notebook")
        plt.figure(figsize=(10, 10))
        sns.scatterplot(x=Xoh, y=self.y, color='green', alpha=0.7, edgecolor=None)

        # Gather model information
        slope_lo, slope, slope_hi = self.slope_data
        intercept_lo, intercept, intercept_hi = self.intercept_data
        plt.plot(X_points, ((X_points * slope) + intercept), color='green', linewidth=2, label='Best fit')
        plt.plot(X_points, ((X_points * slope_lo) + intercept), color='green', linestyle='--', alpha=0.7, label='Confidence bounds')
        plt.plot(X_points, ((X_points * slope_hi) + intercept), color='green', linestyle='--', alpha=0.7)
        plt.plot(X_points, X_points, color='red', linewidth=2, label='y = x')

        # Add vertical and horizontal reference lines
        plt.axvline(x=1, color='black', linestyle='--', linewidth=1.5, label='x = 1')
        plt.axhline(y=1, color='black', linestyle='--', linewidth=1.5, label='y = 1')

        # Improve plot aesthetics
        plt.xscale('log')
        plt.yscale('log')
        plt.xlabel(self.xaxis_label, fontsize=12)
        plt.ylabel(self.yaxis_label, fontsize=12)
        
        # Add legend
        plt.legend(frameon=True, fontsize=11)

        # Remove top and right spines for a cleaner look
        sns.despine()

        # Save figure
        plt.savefig(os.path.join(self.drop_directory, label_oh), dpi=300, bbox_inches='tight')
        plt.close()
        return

    def run_simulation(self, X_subset, y_subset):
        X_subset = add_constant(X_subset)
        model = lm(y_subset, X_subset).fit()
        try:
            slope = model.params[1]
        except:
            slope = np.nan
        return slope

    def subset_simulation_helper(self):
        """ 
        Create an np.nan array with num rows = len(X) and ncolumns = ntrials
        Pull out a random combination subset from original data where subset size is randomly taken from 3 to length of X
        Calculate the (1 - slope per trial)
        For matching rows that were pulled, put this calculated number into the nan array. 
        impute missing data
        k means and plot clusters ...
        """
        xy = np.array([self.X[self.xaxis_label], self.y]).T
        simulated_slopes = []
        region_subset_logic = []
        for k in tqdm.tqdm(range(self.simtrials)):
            numpulls = int(np.random.uniform(4, xy.shape[0]))
            indx = np.random.choice(xy.shape[0], numpulls, replace=False)
            subset = xy[indx]
            simulated_slopes.append(self.run_simulation(X_subset = subset[:,0], y_subset = subset[:,1]))
            
            # Create arrays of zero and 1 for each brain in list
            logical_oh = np.zeros(shape=(xy.shape[0],1))
            logical_oh[indx] = 1
            region_subset_logic.append(logical_oh)
        
        simulated_slopes = np.array(simulated_slopes)
        region_subset_logic = np.array(region_subset_logic)
        region_subset_logic = region_subset_logic.squeeze()

        weighted_results = []
        for region in region_subset_logic.T:
            weighted_results.append(np.nanmean(region*simulated_slopes))
        weighted_results = np.array(weighted_results)
        return weighted_results
    
    def subset_simulation(self):
        if self.convergence_test:
            trial_list = [1,10,100,1000,10000,100000,1000000]
            weighted_results_list = []
            for trial in trial_list:
                self.simtrials = trial
                weighted_results_list.append(self.subset_simulation_helper())
            weighted_results_list = np.array(weighted_results_list)
            standard_deviations = np.std(weighted_results_list,axis=1)
            
            if self.graph_results:
                plt.figure()
                plt.plot(np.array(trial_list),standard_deviations)
                plt.xscale('log')
                plt.savefig(os.path.join(self.drop_directory,"convergence_test_results.jpg"))
                plt.close()

        else:
            weighted_results = self.subset_simulation_helper()        

def cli_argparsing():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pseudo_study',action='store_true',help='If this is set, code will generate pseudo data for testing purposes')
    parser.add_argument('--csv_file',required=False,type=str,help="Full path to csv file containing dataset in LONG format")
    parser.add_argument('--drop_directory',required=True, type=str, help = "Where all final results are saved")

    parser.add_argument('--run_simulation',action='store_true',help='Run a simulation to get weighted slopes for regions')
    parser.add_argument('--run_simulation_convergence',action='store_true',help='Determine if number of simulations produces different weighted slope results')
    parser.add_argument('--graph_results',action='store_true',help='Graph results and save to drop path')
    args = parser.parse_args()
    return args

if __name__=='__main__':
    # Parse command line arguments
    args_oh = cli_argparsing()
    
    # Load in real or pseudo data for analysis
    if args_oh.pseudo_study:
        df = generate_pseudo_data()
    else:
        try:
            df = pd.read_csv(args_oh.csv_file)
        
        except:
            print('Issue with reading csv file. May not have been provided. Using Pseudo data!!')
            df = generate_pseudo_data()

    # Set up and run stability analysis for dataset
    slopeobj = slope_stability(dataframe_oh = df, 
                               drop_directory=args_oh.drop_directory, 
                               simulation = args_oh.run_simulation, 
                               convergence_test=args_oh.run_simulation_convergence, 
                               graph_results=args_oh.graph_results)
    slopeobj()