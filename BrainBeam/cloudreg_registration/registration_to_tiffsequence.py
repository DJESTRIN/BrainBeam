#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This script was written to quickly sbatch process a number of registered brain atlases to target image space via convert_image script. 
"""
import sys,os,glob
sys.path.append('/home/dje4001/lightsheet_cluster/')
import subprocess
from skimage.io import imread
import ipdb


def ConvertIMG(search_paths):
    #Loop over search paths
    for path in search_paths:
        #Search for subjects in registered folder
        subjects=glob.glob(path+'registered/*/downloop_1_labels_to_target_highres.img')
        #Search for registration tiff folder
        for subject in subjects:
            #Set up output folder path
            pre_drop_folder,_=subject.split('downloop_1_labels_to_target_highres')
            output_path=pre_drop_folder+'tiffsequence/'
            
            #Get the raw image sizes in pixels
            basefolder,subjectid=pre_drop_folder.split('registered/')
            images=glob.glob(basefolder+'stitched/'+subjectid+'Ex_647_Em_680/*.tif*')
            for image in images:
                image_oh=imread(image)
                target_image_sizex=image_oh.shape[1]
                target_image_sizey=image_oh.shape[0]
                break
            

            my_command="sbatch --job-name=atlastotarget_convert --mem=300G --partition=sackler-cpu,scu-cpu --mail-type=BEGIN,END,FAIL --mail-user=dje4001@med.cornell.edu --wrap='python convert_image.py --input_image_path {} --output_path {} --target_image_sizex {} --target_image_sizey {} --mode {}'".format(subject,output_path,target_image_sizex,target_image_sizey,'nearest') 
            
            #Create output and run sbatch
            if os.path.exists(output_path):
                print('Converting the following registered atlas to target space:')
                print(subject)
                subprocess.run([my_command],shell=True)
                
            else:
                print('Converting the following registered atlas to target space:')
                print(subject)
                os.mkdir(output_path)
                subprocess.run([my_command],shell=True)


if __name__=='__main__':
    print('Starting the build')
    search_paths=['/athena/listonlab/scratch/dje4001/rabies_cort_control_restain/lightsheet/',
                  '/athena/listonlab/scratch/dje4001/rabies_cort_experimental/lightsheet/']
    ConvertIMG(search_paths)