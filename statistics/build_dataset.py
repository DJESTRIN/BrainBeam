#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This script was written to generate tall data using sbatch induced parrallel computers
"""
import sys,os,glob
sys.path.append('/home/dje4001/lightsheet_cluster/')
from cell_manipulations import *
import ipdb
import subprocess

Tree=Graph(ontology_dict)

def BuildData(search_paths):
    #Loop over search paths
    for path in search_paths:
        #Search for subjects in segmented data folder
        subjects=glob.glob(path+'segmented/*/Ex_647_Em_680/cell_detect_test.json')
        
        #Search for registration tiff folder
        for subject in subjects:
            _,subject_id=subject.split('segmented')
            subject_id,_=subject_id.split('Ex_647_Em_680')
            atlas_path=path+'registered'+subject_id+'tiffsequence/'
            image_path=path+'stitched'+subject_id+'Ex_647_Em_680/'
            output_path=path+'tallformat'+subject_id
            cell_counts_path=subject
            
            #If atlas_path and image path are real, continue
            if os.path.exists(atlas_path) and os.path.exists(image_path) and os.path.isfile(atlas_path+'1.tiff'):
                my_command="sbatch --job-name=converttotall --mem=300G --partition=sackler-cpu,scu-cpu --mail-type=BEGIN,END,FAIL --mail-user=dje4001@med.cornell.edu --wrap='python cell_manipulations.py --image_path {} --atlas_path {} --cell_counts_path {} --output_path {}'".format(image_path,atlas_path,cell_counts_path,output_path) 
                
                if os.path.exists(output_path):
                    print('BELOW IS GOOD:')
                    print(subject)
                    subprocess.run([my_command],shell=True)
                    
                else:
                    os.mkdir(output_path)
                    subprocess.run([my_command],shell=True)
            else:
                print('BELOW IS BAD:')
                print(subject)
            




# image_path = "/athena/listonlab/scratch/dje4001/rabies_cort_control_restain/lightsheet/stitched/20221105_10_35_50_CAGE3811494_ANIMAL1019_VIRUSRABIES_CORTCONTROL/Ex_647_Em_680/"
# atlas_path = "/athena/listonlab/scratch/dje4001/rabies_cort_control_restain/lightsheet/registered/20221105_10_35_50_CAGE3811494_ANIMAL1019_VIRUSRABIES_CORTCONTROL/tiffsequence/"
# cell_counts_path = "/athena/listonlab/scratch/dje4001/rabies_cort_control_restain/lightsheet/segmented/20221105_10_35_50_CAGE3811494_ANIMAL1019_VIRUSRABIES_CORTCONTROL/Ex_647_Em_680/cell_detect_test.json"
# output_path = "/athena/listonlab/scratch/dje4001/rabies_cort_control_restain/lightsheet/tallformat/20221105_10_35_50_CAGE3811494_ANIMAL1019_VIRUSRABIES_CORTCONTROL/"

if __name__=='__main__':
    print('Starting the build')
    search_paths=['/athena/listonlab/scratch/dje4001/rabies_cort_control_restain/lightsheet/',
                  '/athena/listonlab/scratch/dje4001/rabies_cort_experimental/lightsheet/']
    BuildData(search_paths)