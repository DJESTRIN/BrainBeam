#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: validate_numpy_arrays.py
Description: 
Author: David Estrin
"""
import glob
import os
import random
import re
import argparse
import itertools
import numpy as np
import tqdm
import ipdb

def main(root_directory):
    # Get numpy files in list
    pattern = os.path.join(root_directory, "**", "*.npy")
    numpy_files = glob.glob(pattern, recursive=True)
    ipdb.set_trace()

    # Randomly select 100 files to check
    if len(numpy_files) >= 100:
        selected_files = random.sample(numpy_files, 100)
    else:
        print("Less than 100 files")
        selected_files = numpy_files 

    # Set up regular expressioin
    pattern_to_find = r"Ex_.*?_Em_.*?" 
    green = "Ex_488_Em_525"  
    orange = "Ex_561_Em_600"
    red = "Ex_647_Em_680"
    farred = "Ex_785_Em_785"

    # Set up tally system
    same=0
    notsame=0

    # Loop over selected files and compare arrays
    for file in tqdm.tqdm(selected_files):
        # Find all real and corresponding files
        comparisons=[]
        if os.path.isfile(re.sub(pattern_to_find, green, file)):
            comparisons.append(re.sub(pattern_to_find, green, file))
        elif os.path.isfile(re.sub(pattern_to_find, orange, file)):
            comparisons.append(re.sub(pattern_to_find, orange, file))
        elif os.path.isfile(re.sub(pattern_to_find, red, file)):
            comparisons.append(re.sub(pattern_to_find, red, file))
        elif os.path.isfile(re.sub(pattern_to_find, farred, file)):
            comparisons.append(re.sub(pattern_to_find, farred, file))

        for (path1,path2) in itertools.combinations(comparisons,2):
            array1 = np.load(path1)
            array2 = np.load(path2)

            if np.array_equal(array1, array2):
                print("The arrays are identical.")
                same+=1
            else:
                print("The arrays are different.")
                notsame+=1
    return same,notsame

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=str,required=True)
    args=parser.parse_args()
    same,notsame=main(args.input)
    print(f"There were {same} equal arrays and {notsame} not equal arrays")