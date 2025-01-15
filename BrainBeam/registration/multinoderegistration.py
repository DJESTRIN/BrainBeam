#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: multinoderegistration.py
Description: 
Author: David Estrin
Date: 2024-008-15
Version: 1.0
"""
import os,glob
import subprocess
import argparse

""" 
--- Find info ---
(1) Find stitched image path for each subject
(2) Find cell count files for each subject
(3) Create registration output path for each subject 
    (a) Registration output
    (b) atlas drop path
(4) Create common registration folder where all image results will be dropped 
    (a) save a file containing all output folders to monitor?
(5) Rename cell count files to contain channel information and copy/paste this file into registration output directory
(6) Search for force_flips file
(7) Search for force orientation file
(8) Search for align binary mask file 
(9) Make sure log path is set up
(10) Make sure error path is set up
 
--- Run slurm ---
(11) call sbatch with given information to run registration

--- maintenance slurm ---
(12) Run script that continously monitors output directory
    (a) Copies images over to common directory and renames them, making sure they have cage and subject ID in name ...

"""

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
                --wrap='python ./DataMerger.py \
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

