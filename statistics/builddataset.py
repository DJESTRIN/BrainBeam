#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from cell_manipulations import sample_channel
from princeton_ara import Graph
from princeton_ara import *
import glob
import ipdb



def get_dirs(parent_dir):
    # Find cell counts csv files
    ipdb.set_trace()

    # Find atlas tif stack -- does 0.tif exist?

    # Find stitched image path --

    # If all three exist, create output folder and add to list
    glob.glob(parent_dir)

def run_dirs(big_list,ontology_dict,ara_file):
    total_samples=len(big_list)
    for n,(image_path,atlas_path,cell_counts_path,output_path) in enumerate(big_list):
        print(f'On Sample {n} out of {total_samples}')
        Tree=Graph(ontology_dict)
        channel=sample_channel(image_path,atlas_path,cell_counts_path,output_path,5,Tree,ara_file)
        channel.forward()
    return

if __name__=='__main__':
    parent_dir="/athena/listonlab/scratch/dje4001/lightsheet_scratch/rabies_cort_experimental_cohort2/"
    get_dirs(parent_dir)
    run_dirs()

