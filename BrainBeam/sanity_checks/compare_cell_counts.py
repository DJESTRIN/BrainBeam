#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module name: compare_cell_counts.py
Description: Takes two cell_counts.csv files as inputs and compares the percent of overlap for those files. 
Author: David Estrin
Version: 1.0
Date: 11-05-2024
"""
import argparse
import pandas as pd
import numpy as np

def compare_csv_files(file1,file2,file_names=None):
    # Read in csv files to dataframes
    f1=pd.read_csv(file1)
    f2=pd.read_csv(file2)

    # align dataframes and calculate the overlap
    af1, af2 = f1.align(f2, join='inner')
    matches = (af1[['x', 'y', 'z']] == af2[['x', 'y', 'z']]).all(axis=1)
    total_overlap = matches.mean()*100

    # Calculate number of rows that do not match per dataset
    f1_cor = set(f1[['x', 'y', 'z']].itertuples(index=False, name=None))
    f2_cor = set(f2[['x', 'y', 'z']].itertuples(index=False, name=None))
    f1_not_in_f2 = f1_cor - f2_cor
    f2_not_in_f1 = f2_cor - f1_cor
    num_f1 = len(f1_not_in_f2)
    num_f2 = len(f2_not_in_f1)
    per_f1 = len(f1_not_in_f2)/len(f1_cor)
    per_f2 = len(f2_not_in_f1)/len(f2_cor)

    print_statement=f"""These files contain {total_overlap}% overlap. \n 
        File 1 contains {len(f1_cor)} total cells, where {num_f1} cells (or {per_f1} %) are unique and not in File 2. \n 
        File 2 contains {len(f2_cor)} total cells, where {num_f2} cells (or {per_f2} %) are unique and not in File 1."""
    
    print(print_statement)


if __name__=='__main__':
    # Parse command line inputs
    parser=argparse.ArgumentParser()
    parser.add_argument('--file1',type=str,required=True,help='A directory to first csv file containing counts. For my project, I use this for the RABIES channel')
    parser.add_argument('--file2',type=str,required=True,help='A directory to first csv file containing counts. For my project, I use this for the helper_virus channel')
    args=parser.parse_args()
    compare_csv_files(args.file1,args.file2,file_names=['Rabies Channel','Helper_virus_channel'])

