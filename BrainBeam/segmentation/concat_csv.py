#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: concat_csv.py
Description: 
Author: David Estrin
"""
import pandas as pd
import os, glob
import argparse

def find_csv(path):
    pathsearch = path + '/*/*/*ities.csv'
    local_csvfiles = glob.glob(pathsearch, recursive=True)
    output_file = path + '/cell_counts.csv'
    return local_csvfiles, output_file

def concat_csv(files, outputfilename):
    csvfiles = []
    
    for filename in files:
        df = pd.read_csv(filename, index_col=None)
        csvfiles.append(df)

    finaldf = pd.concat(csvfiles, axis=0, ignore_index=True)
    finaldf.to_csv(outputfilename, index=False)

    # **Delete the original CSV files after successful merge**
    for filename in files:
        try:
            os.remove(filename)
            print(f"Deleted: {filename}")
        except Exception as e:
            print(f"Error deleting {filename}: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_dir', required=True)
    args = parser.parse_args()

    csvfiles, outputfilename = find_csv(args.input_dir)
    concat_csv(csvfiles, outputfilename)