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
import glob,os
from tqdm import tqdm
import re
import ipdb

def compare_csv_files(file1,file2,file_names=None,print_out=False):
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

    if print_out:
        print_statement=f"""These files contain {total_overlap}% overlap. \n 
            File 1 contains {len(f1_cor)} total cells, where {num_f1} cells (or {per_f1} %) are unique and not in File 2. \n 
            File 2 contains {len(f2_cor)} total cells, where {num_f2} cells (or {per_f2} %) are unique and not in File 1."""
        
        print(print_statement)
    
    return total_overlap, f1_cor, num_f1, per_f1, f2_cor, num_f2, per_f2

def find_cells_csv(root_dir, target_file='cell_counts.csv', max_depth=3):
    matching_files = []
    total_dirs = sum([len(dirs) for _, dirs, _ in os.walk(root_dir)])  # Count total directories to set tqdm

    for dirpath, dirnames, filenames in tqdm(os.walk(root_dir), total=total_dirs, desc="Searching directories"):
        current_depth = dirpath[len(root_dir):].count(os.sep)
        
        if current_depth > max_depth:
            continue
        
        # Check if the target file is in the current directory and if 'Ex_ch1' is in the path
        if target_file in filenames and 'Ex_647_Em_680' in dirpath:
            matching_files.append(os.path.join(dirpath, target_file))

    return matching_files

def get_info(file_oh, pattern = r'CAGE(\d+)_ANIMAL(\d+)_SEX(\w+)_CORT(.+)'):
    ipdb.set_trace()
    match = re.search(pattern, file_oh)

    if match:
        cage_number = match.group(1)  # Extract the cage number
        animal_number = match.group(2)  # Extract the animal number
        sex = match.group(3)  # Extract the sex
        cort = match.group(4)  # Extract the cortex information
        return cage_number,animal_number,sex,cort
    else:
        return 'NA','NA','NA','NA'


def print_info(cage_number,animal_number,sex,cort,total_overlap, f1_cor, num_f1, per_f1, f2_cor, num_f2, per_f2):
    print(f"====== Cage: {cage_number} Subject: {animal_number} Sex: {sex} Group: {cort} ========\n")
    print_statement=f""" {total_overlap}% overlap. \n 
                {len(f1_cor)} total rabies+ cells, where {num_f1} cells (or {per_f1} %) are not helper+. \n 
                {len(f2_cor)} total helper+ cells, where {num_f2} cells (or {per_f2} %) are not rabies+."""
    print(print_statement)
    print("============================================\n")

def full_dir_analyses(root_dir):
    # Get rabies channel data
    rabies_files = find_cells_csv(root_dir)

    # Get corresponding helper virus channel file
    file_pairs=[]
    for file in rabies_files:
        for helper_channel in ['Ex_561_Em_600','Ex_488_Em_525','Ex_785_Em_785']:
            helper_file = file
            helper_file = helper_file.replace('Ex_647_Em_680',helper_channel)
            if os.path.isfile(helper_file):
                file_pairs.append([file,helper_file])
                break
    
    for file1,file2 in file_pairs:
        total_overlap, f1_cor, num_f1, per_f1, f2_cor, num_f2, per_f2 = compare_csv_files(file1,file2)
        cage_number,animal_number,sex,cort = get_info(file1)
        print_info(cage_number,animal_number,sex,cort,total_overlap, f1_cor, num_f1, per_f1, f2_cor, num_f2, per_f2)

if __name__=='__main__':
    # Parse command line inputs
    parser=argparse.ArgumentParser()
    parser.add_argument('--file1',type=str,required=False,help='A directory to first csv file containing counts. For my project, I use this for the RABIES channel')
    parser.add_argument('--file2',type=str,required=False,help='A directory to first csv file containing counts. For my project, I use this for the helper_virus channel')
    parser.add_argument('--root_dir',type=str,required=False,help='Root directory to run analysis')
    args=parser.parse_args()
    if args.root_dir:
        full_dir_analyses(args.root_dir)
    else:
        compare_csv_files(args.file1,args.file2,file_names=['Rabies Channel','Helper_virus_channel'])

