#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CANCELLED development of code: It makes more sense to take image stack and bring it into syglass. 

    Region HeatMap 
    Takes brain, brain region of interest (atlas_id), 
    and generates a MIP of subregion, with segmentations
    also with heatmaps.
"""
import os 
import sys
sys.path.insert(0,'/home/dje4001/CloudReg/')
from CloudReg.cloudreg.scripts.ARA_stuff.parse_ara import *
ara_file="/home/dje4001/CloudReg/cloudreg/scripts/ARA_stuff/ara_ontology.json"
"downloop_1_A.mat"
import scipy.io.loadmat as lm


class set_up_paths:
    def __init__(self, sample_path,atlas_path,registration_path,output_parent_dir):
        self.sample_path=sample_path
        self.atlas_path=atlas_path
        self.registration_path=registration_path
        self.output_parent_dir=output_parent_dir
        self.check_path()
    
    def check_path(self):
        """ double check paths to see if real"""
        if os.path.exists(self.sample_path) or os.path.exists(self.atlas_path) or os.path.exists(self.registration_path):
            raise TypeError("One of the data paths does not exist") 
        
        #Generate output path if it does not exist. 
        isExist=os.path.exists(self.output_parent_dir)
        if not isExist:
            os.makedirs(self.output_parent_dir)

class region_images(set_up_paths):
    def set_up_output(self,region_num):
        """ Set up sub directories of output path """
        subdirs=[self.output_parent_dir+"atlas/", self.output_parent_dir+"sample/", self.output_parent_dir+"segmentation/"]

        for subdir_oh in subdirs:        
            #Generate output path if it does not exist. 
            isExist=os.path.exists(subdir_oh)
            if not isExist:
                os.makedirs(subdir_oh)
        
        self.region_num=region_num #allan brain atlas id for region of interest.
        #Example, if Nuclues accumbens is what needs to be graphed and its allan atlas_id=10, then input 10. 
        
    def find_subregions_of_input(self,ara_file):
        """ Using ARA file, find all children of subregion of interest """
        f = json.load(open(ara_file, "r"))
        tree=build_tree(f)

            

#Bring in paths
#Set up output path
    #within directory create:
        #coronal section
        #atlas coronal section
        #Heatmap coronal section
        #Segmentation coreonal section
#Convert atlas_id's to list (can be one or more)
#Loop over atlas_ids
#Loop through atlas tif stack:
    #if atlas image contains region of interest:
        #copy image to atlas coronal section directory
        #copy corresponding images and segmentations to respective directories
        #get all coordinates of region in image. 
        #compute bounding box, compare to previos bounding box:
            #if any coordiante is bigger, update boudnign box to generate biggest square
            
#Crop tiff stacks in output dirs based on the largest bounding boxes. 
#Generate MIP=> can be done for coronal, sagitall and axial directions. 
    #Loop over cropped images
        #Perform transform
        #Get max of image and segmentaiton and generate a line in the coronal plain. 
        #For atlas, use middle slice.
    #Generate image
        #sample + atlas
        #sample + atlas + cells
        #atlas + heatmap
        

            

#Bring in paths
#Set up output path
    #within directory create:
        #coronal section
        #atlas coronal section
        #Heatmap coronal section
        #Segmentation coreonal section
#Convert atlas_id's to list (can be one or more)
#Loop over atlas_ids
#Loop through atlas tif stack:
    #if atlas image contains region of interest:
        #copy image to atlas coronal section directory
        #copy corresponding images and segmentations to respective directories
        #get all coordinates of region in image. 
        #compute bounding box, compare to previos bounding box:
            #if any coordiante is bigger, update boudnign box to generate biggest square
            
#Crop tiff stacks in output dirs based on the largest bounding boxes. 
#Generate MIP=> can be done for coronal, sagitall and axial directions. 
    #Loop over cropped images
        #Get max of image and segmentaiton and generate a line in the coronal plain. 
        #For atlas, use middle slice.
    #Generate image
        #sample + atlas
        #sample + atlas + cells
        #atlas + heatmap