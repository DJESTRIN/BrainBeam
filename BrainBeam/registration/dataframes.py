#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: dataframes.py
Description: From registration output, convert data into a tall formatted dataframe  
Author: David Estrin
Date: 2024-008-15
Version: 2.0
Usage: python DataMerger.py --input data.csv --output results.csv
"""
import json
import numpy as np 
from BrainBeam.statistics.princeton_ara import *
from tqdm import tqdm
import pandas as pd
import argparse
import os, glob
import ipdb

class lightsheet_volume_data():
    """ Get medi data regarding subject's name, group etc from path"""
    def __init__(self,data_path):
        self.data_path = data_path
        self.gather_data() # Get primary data 

    def strip_file_to_name(self,path_oh):
        # Get cage id number
        _,cage = path_oh.lower().split('cage')
        cage = cage.split('_')[0]

        # Get animal id number
        _, animal = path_oh.lower().split('animal')
        animal = animal.split('_')[0]

        # Get group id
        if 'cort' in path_oh.lower():
            group='cort'
        else:
            group='control'
        return cage, animal, group

    def gather_data(self):
        # Find all mapped files in final path
        mapped_files = glob.glob(os.path.join(self.data_path,r"**\*mapped*.npy"),recursive=True)
        
        # Load in data from files as numpy array
        # Get medidata containing animal info into list
        self.data = []
        self.medidata = []
        for npfile in mapped_files:
            self.data.append(np.load(npfile))
            self.medidata.append(self.strip_file_to_name(path_oh = npfile))

class array_to_dataframe():
    def __init__(self, lightsheet_volume_object, data_path):
        self.data_path = data_path
        self.lightsheet_volume_object = lightsheet_volume_object

        # Dataframe output files
        self.tall_dataframe_output_file = None
        self.wide_dataframe_output_file = None
    
    def volume_to_dataframe(self):
        """ Convert numpy arrays into dataframes """
        data = self.lightsheet_volume_object.data
        medidata = self.lightsheet_volume_object.medidata

        for data_oh, medidata_oh in zip(data,medidata):
            ipdb.set_trace()
            # Go through each key in the atlas and get total cell counts on right and left side
            # Get normalized cell count
            # Get number of starter cells and normalize by starter cells... though not verified


    # def find_midline(self):
    #     """ Find and save midline of numpy array """
    #     self.midline = self.array.shape[0] // 2

    # def array_to_tallformat(self):
    #     """
    #       Subject, Cage, SUID, Group, Channel, Brain Region name (lowest level), Brain Region ID,  Side (Ipsi or Contra), Number of cells, Normalized cell count
    #     """
    #     ipdb.set_trace()
    #     # Loop over every ID in associated atlas via np unique 
    #         # Get Brain region name
    #         # Loop over channels if more than one
    #             # For all coordinates where ID exists, get total number of cells per side
    #             # For all coordinates where ID exists, normalized number of cells per side by summing ... 

    # def save_tallformat_dataframe(self):
    #     self.df.to_csv(os.path.join(self.data_path,"tall_df.csv"))

    # def __call__(self):
    #     """ Straight forward pipeline for converting 4D array to a tall format dataframe """
    #     self.load_array()
    #     self.find_midline()
    #     self.array_to_tallformat()
    #     self.save_tallformat_dataframe()

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data_path',type=str, help="Full path containing 4D numpy file")
    args = parser.parse_args()

    # Get medi data for current subject
    medobj = lightsheet_volume_data(data_path = args.data_path)

    ipdb.set_trace()
    # Create and output tall formatted data frame
    DFobj = array_to_dataframe(medidata_obj = medobj, data_path = args.data_path)
    DFobj()
