#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

"""
import os
import glob
import pandas as pd

directories=["/athena/listonlab/scratch/dje4001/rabies_cort_experimental/lightsheet/tallformat/",
             "/athena/listonlab/scratch/dje4001/rabies_cort_control_restain/lightsheet/tallformat/"]

#Get csv files
list_of_files=[]
for directory in directories:
    for root,dirs,files in os.walk(directory):
        for file in files:
            if file.endswith(".csv"):
                list_of_files.append(os.path.join(root,file))

os.chdir("/athena/listonlab/scratch/dje4001/")
combined_csv=pd.concat([pd.read_csv(f) for f in list_of_files])
combined_csv.to_csv("pseudorabies_dataset",index=False)