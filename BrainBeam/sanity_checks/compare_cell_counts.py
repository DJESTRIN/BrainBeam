#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module name: compare_cell_counts.py
Description: Takes two cell_counts.csv files as inputs and compares the percent of overlap for those files. 
Author: David Estrin
Version: 1.0
Date: 11-05-2024
"""
import ipdb
import argparse
import pandas as pd
import numpy as np

def compare_csv_files(file1,file2):
    f1=pd.read_csv(file1)
    f2=pd.read_csv(file2)
    af1, af2 = f1.align(f2, join='inner')
    ipdb.set_trace()
    exact_matches = (af1[['x', 'y', 'z']] == af2[['x', 'y', 'z']]).all(axis=1)
    ipdb.set_trace()

if __name__=='__main__':
    # Parse command line inputs
    parser=argparse.ArgumentParser()
    parser.add_argument('--file1',type=str,required=True)
    parser.add_argument('--file2',type=str,required=True)
    args=parser.parse_args()
    compare_csv_files(args.file1,args.file2)

