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

class medidata():
    """ Get medi data regarding subject's name, group etc from path"""
    def __init__(self,data_path):
        self.data_path = data_path

    def gather_data(self):
        ipdb.set_trace()

class tallformat(medidata):
    def __init__(self, medidata_obj, data_path):
        self.data_path = data_path
        self.mapped_array_file = os.path.join(self.data_path,"mapped_array.npy")
        self.medidata = medidata_obj
    
    def load_array(self):
        self.array = np.load(self.mapped_array_file)

    def find_midline(self):
        """ Find and save midline of numpy array """
        self.midline = self.array.shape[0] // 2

    def array_to_tallformat(self):
        """
          Subject, Cage, SUID, Group, Channel, Brain Region name (lowest level), Brain Region ID,  Side (Ipsi or Contra), Number of cells, Normalized cell count
        """
        ipdb.set_trace()
        # Loop over every ID in associated atlas via np unique 
            # Get Brain region name
            # Loop over channels if more than one
                # For all coordinates where ID exists, get total number of cells per side
                # For all coordinates where ID exists, normalized number of cells per side by summing ... 

    def save_tallformat_dataframe(self):
        self.df.to_csv(os.path.join(self.data_path,"tall_df.csv"))

    def __call__(self):
        """ Straight forward pipeline for converting 4D array to a tall format dataframe """
        self.load_array()
        self.find_midline()
        self.array_to_tallformat()
        self.save_tallformat_dataframe()

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data_path',type=str, help="Full path containing 4D numpy file")
    args = parser.parse_args()

    # Get medi data for current subject
    medobj = medidata(data_path = args.data_path)
    medobj.gather_data()

    # Create and output tall formatted data frame
    DFobj = tallformat(medidata_obj = medobj, data_path = args.data_path)
    DFobj()
