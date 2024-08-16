#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: startercell_df.py
Description: This script will take info about the total number of cells per channel and starter cells and merge into a single dataframe for all paths given
Author: David Estrin
Date: 2024-08-16
Version: 1.0
"""
from DataMerger import *
import os,glob

def find_all_objects(root_paths):
    if len(root_paths)>2:
        # Set up list for final dataframe
        starter_data=[]

        # Loop over root paths if multiple
        for root_path in root_paths:
            tallformat_path = os.path.join(root_path,'lightsheet/tallformat/')
            search_path = tallformat_path+"*/rabies_sample_object_*.pkl"
            rabies_object_path = glob.glob(search_path)[0]
            rabies_obj = rabies_sample.load(rabies_object_path)
            rabies_obj.total_coexpressing_cells

