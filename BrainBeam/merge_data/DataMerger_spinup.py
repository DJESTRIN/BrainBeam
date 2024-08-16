#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: DataMerger_spinup.py
Description: Finds common directories and passes them to DataMerger script via sbatch  
Author: David Estrin
Date: 2024-008-15
Version: 1.0
"""
import os,glob
import subprocess
import argparse

def paths_to_list(search_paths):
    final_list=[]
    for path in search_paths:
        #Search for subjects in segmented data folder
        subjects=glob.glob(path+'segmented/*/Ex_647_Em_680/cell_counts.csv')

        # Loop over subjects to find corresponding folders
        for subject in subjects:
            _,subject_id=subject.split('segmented')
            subject_id,_=subject_id.split('Ex_647_Em_680')

            atlas_path=path+'registered'+subject_id+'tiffsequence/' #atlas path
            image_path=path+'stitched'+subject_id+'/' #image path
            output_path=path+'tallformat'+subject_id #output path
            cell_counts_path=subject # cell counts path

            final_list.append([atlas_path,image_path,output_path,cell_counts_path])
    return final_list

def submit_datamerge_jobs(dir_list):
    for (atlas_path,image_path,output_path,cell_counts_path) in dir_list:
        # Check if paths are real
        if os.path.exists(atlas_path) and os.path.exists(image_path) and os.path.isfile(atlas_path+'1.tiff'):
            my_command=f"sbatch --job-name=merge_data_to_tallformat \
                --mem=300G \
                --partition=scu-cpu \
                --mail-type=BEGIN,END,FAIL \
                --mail-user=dje4001@med.cornell.edu \
                --wrap='python cell_manipulations.py \
                --image_path {image_path} \
                --atlas_path {atlas_path} \
                --cell_counts_path {cell_counts_path} \
                --output_path {output_path}'"
                
            if not os.path.exists(output_path):
                os.mkdir(output_path)
                
            subprocess.run([my_command],shell=True)

        else:
            if not os.path.exists(atlas_path):
                print(f"Problem with {atlas_path}")
            
            if not os.path.exists(image_path):
                print(f"Problem with {image_path}")

            if not os.path.isfile(atlas_path+'1.tiff'):
                print(f"Problem with {atlas_path} first tiff image")

def update_directory_naming(input_dir):
    """ Make sure the final word in directory path is actually lightsheet """
    normalized_path = os.path.normpath(input_dir)
    last_folder = os.path.basename(normalized_path)
    if last_folder != 'lightsheet':
        return os.path.join(normalized_path, 'lightsheet')
    return normalized_path

if __name__=='__main__':
    print('Starting to Build final dataset!')
    
    # Parse command line inputs
    parser = argparse.ArgumentParser(description="Get all main directories")
    parser.add_argument('--input_directories', nargs='+', help='A list of directories to run data merging on')
    args = parser.parse_args()

    # Collect list of all directories and submit sbatch jobs
    for input_dir in args.input_directories:
        input_dir=update_directory_naming(input_dir)
        subject_list=paths_to_list(input_dir)
        submit_datamerge_jobs(subject_list)

