#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: checkrepeats.py
Description: This code is meant to determine whether channels (or associated files like numpy arrays) are complete repeats of one another. This code is not
    a part of the main pipeline and is a diagnostic tool.
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
from PIL import Image
import ipdb

class checkrepeats:
    def __init__(self,root_directory,selection_size=100,pattern="*.tiff",recursive=True):
        self.pattern=pattern
        self.search_pattern=os.path.join(root_directory, "**", self.pattern)
        self.files = glob.glob(self.search_pattern,recursive=recursive)

        # Randomly select 100 files to check
        if len(self.files) >= 100:
            self.files = random.sample(self.files, selection_size)
        else:
            print("Less than 100 files")

        # Set up remaining
        self.setup()

    def setup(self):
        # Set up regular expressioin
        self.pattern_to_find = r"Ex_.*?_Em_.*?/" 
        self.green = "Ex_488_Em_525/"  
        self.orange = "Ex_561_Em_600/"
        self.red = "Ex_647_Em_680/"
        self.farred = "Ex_785_Em_785/"
        self.same=0
        self.notsame=0

    def find_overlapping_files(self):
        for file in tqdm.tqdm(self.files):
            # Find all real and corresponding files
            comparisons=[]
            if os.path.isfile(re.sub(self.pattern_to_find, self.green, file)):
                comparisons.append(re.sub(self.pattern_to_find, self.green, file))
            if os.path.isfile(re.sub(self.pattern_to_find, self.orange, file)):
                comparisons.append(re.sub(self.pattern_to_find, self.orange, file))
            if os.path.isfile(re.sub(self.pattern_to_find, self.red, file)):
                comparisons.append(re.sub(self.pattern_to_find, self.red, file))
            if os.path.isfile(re.sub(self.pattern_to_find, self.farred, file)):
                comparisons.append(re.sub(self.pattern_to_find, self.farred, file))

            for (path1,path2) in itertools.combinations(comparisons,2):
                # Make sure it is not the same path twice
                if path1==path2:
                    continue

                # Compare the files depending on file type
                if self.pattern=="*.npy":
                    self.comp_images(path1,path2)
                elif self.pattern=="*.tiff":
                    self.comp_arrays(path1,path2)
                else:
                    self.comp_filesizes(path1,path2)

    def comp_images(self,path1,path2):
        # Load in images as numpy arrays
        array1 = np.array(Image.open(path1))
        array2 = np.array(Image.open(path2))

        # Compare array sizes
        if np.array_equal(array1, array2):
            self.same+=1
        else:
            self.notsame+=1

    def comp_arrays(self,path1,path2):
        # Load in numpy arrays
        array1 = np.load(path1)
        array2 = np.load(path2)

        # Compare array sizes
        if np.array_equal(array1, array2):
            self.same+=1
        else:
            self.notsame+=1

    def comp_filesizes(self,path1,path2):
        # Get file sizes
        size1=os.path.getsize(path1)
        size2=os.path.getsize(path1)

        # Compare file sizes
        if np.array_equal(size1, size2):
            self.same+=1
        else:
            self.notsame+=1

if __name__=='__main__':
    # Parse command line arguments
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=str,required=True)
    parser.add_argument('--pattern',type=str,required=True)
    args=parser.parse_args()

    # Check for repeats
    checker=checkrepeats(args.input,**({'pattern': args.pattern} if hasattr(args, 'pattern') else {}))
    checker.find_overlapping_files()
    print(f"There were {checker.same} equal arrays and {checker.notsame} not equal arrays")