#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module name: dataframe_meta_data.py
Description: Investigate number of brain regions per mouse in dataframe to determine uniformity in data
Author: David Estrin
Version: 1.0
Date: 11-11-2024
"""
import pandas as pd
import os,glob
import ipdb

def load_data_frames(root_directory,search_pattern):
    # Search for files based on root dir and pattern
    files=glob.glob(os.path.join(root_directory,search_pattern))

    # Open files and append to list
    all_dataframes=[]
    for file in files:
        df=pd.read_csv(file,index_col=None)
        all_dataframes.append(df)

    return all_dataframes

def check_dataframe(df):
    df['subjectid_updated'] = df['subjectid'].str.replace(r'ANIMAL(\d)\b', r'ANIMAL0\1', regex=True)
    df['uid']=df['cage']+df['subjectid_updated']
    Num_uniq_regions = df.groupby(['uid'])['location'].nunique()
    print(Num_uniq_regions)

if __name__=='__main__':
    dataframes = load_data_frames(root_directory=r'C:\Users\listo\level_analysis\results_20241115_120957',search_pattern='conor*level*.csv')
    for i,dfoh in enumerate(dataframes):
        print(f'===Stats for file # {i}===')
        check_dataframe(df=dfoh)