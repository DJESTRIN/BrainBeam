#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: cellalignment.py
Description: The point of this algorithm is to:
    (1) Downsample stitched data to atlas size
    (2) Downsample cell coordinates to atlas size
    (3) Map cell coordinates to 3D mask where cells within same voxel are aggregated. 
        Ex, a voxel containing 2 cells equals 2.
    (4) Run registration for raw data as well as cellcountmask to atlas space
    (5) The final output will be a saved 3d numpy array for the registered brain and the cell counts. 
Author: David Estrin
Date: 2024-12-11
Version: 1.0
"""
import pandas as pd
import numpy as np
import ipdb
import os, glob
import pickle
from BrainBeam.registration.padding import zero_pad_arrays
from BrainBeam.registration.transforms import *

"""
Load cell count files
    if 1, do thing
    if multiple, do thing multiple times
    if none

Convert cell counts to binary mask aggregate image [0 to inf]
    Down sample coordinate space from original image size to ds size
    Create binary aggregate mask from DS data

Apply all transformations (in correct order) to the mask image
    Do not forget any zero padding 

Final path should contain:
    (1) all transformation files
    (2) the orginal moving image
    (3) transformed moving image
    (4) original cell mask
    (5) transformed cell mask
    (6) the target image
    (7) the atlas associated with target image
    (8) a way to get atlas hierarchy dict ...

Data is now ready for merger code which will put all data into dataframes ...
"""

class cellalignment():
    def __init__(self, zp_id_atlas, 
                 zp_template_atlas, 
                 ds_zp_transformed_moving_image, 
                 drop_path, 
                 cell_count_files = None):
        self.zp_id_atlas = zp_id_atlas
        self.zp_template_atlas = zp_template_atlas
        self.ds_zp_transformed_moving_image = ds_zp_transformed_moving_image
        self.drop_path = drop_path # Path containing pkl transformation files
        self.cell_count_files = cell_count_files

        # Set default as None, updated via method
        self.new_x_dim = None
        self.new_y_dim = None
        self.new_z_dim = None
        self.new_x_pad_dim = None
        self.new_y_pad_dim = None
        self.new_z_pad_dim = None
        self.original_x_dim = None
        self.original_y_dim = None
        self.original_z_dim = None
    
    def update_coordinate_systems(self, new_x_dim, new_y_dim, new_z_dim, original_x_dim, original_y_dim, original_z_dim):
        # Set dimensions for new and original arrays for reference by code
        self.new_x_dim = new_x_dim
        self.new_y_dim = new_y_dim
        self.new_z_dim = new_z_dim
        self.new_x_pad_dim = self.ds_zp_transformed_moving_image.shape[0]
        self.new_y_pad_dim = self.ds_zp_transformed_moving_image.shape[1]
        self.new_z_pad_dim = self.ds_zp_transformed_moving_image.shape[2]
        self.original_x_dim = original_x_dim
        self.original_y_dim = original_y_dim
        self.original_z_dim = original_z_dim

    def __call__(self):
        # Load in cell coordinates for all files
        self.read_cell_count_file()

        # Down sample cell coordinate system
        if self.skip_flag: # Skip if no files given
            return
        else:
            self.downsample_cell_coordinate_system()

        # Convert cell coordinates to aggregate mask
        self.cell_coordinates_to_aggregate_mask()

        # Grab alignment file(s) data
        self.gather_transformations()

        # Apply transform(s) to aggregate mask
        self.transform_cell_mask()
        
    def read_cell_count_file(self):
        self.cell_coordinates=[]
        if len(self.cell_count_files)==1:
            self.cell_coordinates.append(pd.read_csv(self.cell_count_file).to_numpy())

        elif len(self.cell_count_files)>1:
            for i in range(len(self.cell_count_files)):
              self.cell_coordinates.append(pd.read_csv(self.cell_count_file).to_numpy())

        else:
            self.skip_flag = True
            print('No cell coordinate files provided, so all cell alignment code will be skipped')

    def downsample_cell_coordinate_system(self):
        # Check and make sure parameters were defined
        if self.original_x_dim is None or self.original_y_dim is None or self.original_z_dim is None:
            raise("User must call update_coordinate_systems method before call to cell alignment.")
        elif self.original_x_dim is None or self.original_y_dim is None or self.original_z_dim is None:
            raise("User must call update_coordinate_systems method before call to cell alignment.")

        # Determine new scaling... must be moving image orignal prior to zero padding. 
        self.x_factor = self.new_x_dim/self.original_x_dim
        self.y_factor = self.new_y_dim/self.original_y_dim
        self.z_factor = self.new_z_dim/self.original_z_dim
 
        # Downsample cell coordinates based on scaling factors
        self.ds_cell_coordinates_all=[]
        for cell_list in self.cell_coordinates:
            self.ds_cell_coordinates = []
            for cell in cell_list:
                x,y,z = cell
                ds_x, ds_y, ds_z = int(round(x*self.x_factor)), int(round(y*self.y_factor)), int(round(z*self.z_factor))

                # Clip any values that are accidently greater than ds dimensions.
                # However, this code should ideally not be used
                if ds_x>self.new_x_dim:
                    ds_x=int(self.new_x_dim)

                if ds_y>self.new_y_dim:
                    ds_y=int(self.new_y_dim)

                if ds_z>self.new_z_dim:
                    ds_z=int(self.new_z_dim)

                # Append new coordinates to the list
                self.ds_cell_coordinates.append([ds_x, ds_y, ds_z])

            # Convert to a numpy array and make sure no values are greater then dims
            self.ds_cell_coordinates_all.append(np.asarray(self.ds_cell_coordinates))

    def cell_coordinates_to_aggregate_mask(self):
        self.coordinate_mask_all = []
        for cell_list in self.ds_cell_coordinates_all:
            # Generate 3D array of zeros
            self.coordinate_mask_oh = np.zeros((self.new_x_dim,self.new_y_dim,self.new_z_dim), dtype=int)

            # Aggregate total number of cells per voxel in 3d mask
            for cell in cell_list:
                x, y, z = cell
                self.coordinate_mask_oh[x, y, z] += 1
            
            # Append numpy array to list
            self.coordinate_mask_all.append(self.coordinate_mask_oh)

    def gather_transformations(self):
        """ Through self.drop_dir, code will find all transform files, open them and save as attributes for nonrigid and rigid seperately.
            Files must end with an integer or will not be included. Integer is strictly for determining order of application to image volumes."""
        def transform_sort(full_file_path):
            nameoh = full_file_path.split('_')[-1]
            return int(nameoh.split('.')[0])

        # get rigid transformations including stretching
        rigid_transform_files = glob.glob(os.path.join(self.drop_path,"*rigid_only*.pkl"), key=transform_sort)
        self.rigid_transforms = []
        self.rigid_transform_types = []
        for file in rigid_transform_files:
            # Open file
            with open(file, "rb") as f:
                transform_oh = pickle.load(f)

            # Add to list
            self.rigid_transforms.append(transform_oh)

            # determine rigid transform type
            if "stretch" in file:
                self.rigid_transform_types.append(1)
            else:
                self.rigid_transform_types.append(0)
            
        # get non-rigid transformations
        nonrigid_transform_files = glob.glob(os.path.join(self.drop_path,"*nonrigid*.pkl"), key=transform_sort)
        self.nonrigid_transforms = []
        for file in nonrigid_transform_files:
            # Open file
            with open(file, "rb") as f:
                transform_oh = pickle.load(f)

            # Add to list
            self.nonrigid_transforms.append(transform_oh)

    def transform_cell_mask(self):
        """ Apply transformations to aggregate mask """
        self.transformed_volumes = []
        for maskoh in self.coordinate_mask_all:
            transformed_mask = maskoh.copy()

            # Add zero padding to aggregate mask
            template_array = np.zeros((self.new_x_pad_dim, self.new_y_pad_dim, self.new_z_pad_dim))
            transformed_mask, _ = zero_pad_arrays(array1=transformed_mask, array2=template_array)

            # Perform rigid transformations
            for transform_oh, transform_type in zip(self.rigid_transforms,self.rigid_transform_types):
                if transform_type==0:
                    transformed_mask = rigid_transform(best_params = transform_oh,
                                                       moving_image = sitk.GetImageFromArray(transformed_mask), 
                                                       fixed_image = sitk.GetImageFromArray(self.zp_template_atlas))
                elif transform_type==1:
                    transformed_mask = stretch_transform(best_params = transform_oh, 
                                                         moving_image = sitk.GetImageFromArray(transformed_mask), 
                                                         fixed_image = sitk.GetImageFromArray(self.zp_template_atlas))
                else:
                    raise("Transform type should be either 0 or 1. Other type given")
                
            # Perform Non Rigid transformation(s)
            for transform_oh in self.nonrigid_transforms:
                transformed_mask = nonrigid_transform(best_params = transform_oh,
                                                      moving_image = sitk.GetImageFromArray(transformed_mask), 
                                                      fixed_image = sitk.GetImageFromArray(self.zp_template_atlas))

            self.transformed_volumes.append(transformed_mask)
    
    def generate_4D_array(self):
        """ Save the final array (4D) where 3D are Height, Width, Depth
            4th dimension contains:
                Atlas image -- the acutal ARA
                Template image --  orignal template image from ARA
                Moving image -- Transformed raw data image
                Aggregate Cell Count Mask -- the mask containing values [0-inf) for number of cells in voxel. 

            Output will be a numpy array 
            """

        # Put all relevant arrays into a single array
        mapped_array = np.stack([self.zp_id_atlas, self.zp_template_atlas, self.ds_zp_transformed_moving_image], axis=3)
        for cell_list in self.transformed_volumes:
            mapped_array = np.stack([mapped_array,np.array(cell_list)],axis=3)

        # Save data into numpy file 
        self.mapped_array = mapped_array
        np.save(os.path.join(self.drop_path,'mapped_array.npy'), self.mapped_array) 

def main():
    print(' No code in cell alignment main function yet. This is a place holder')

if __name__=='__main__':
    main()

"""
Here is an example of how this class is meant to be run in the registration script ... 

from BrainBeam.registration.cellalignment import cellalignment # Import package

cell_alignment_obj = cellalignment(zp_id_atlas, zp_template_atlas, ds_zp_transformed_moving_image, drop_path) # create the object
cell_alignment_obj.update_coordinate_systems(new_x_dim, new_y_dim, new_z_dim, original_x_dim, original_y_dim, original_z_dim) # add the coordinate system data
cell_alignment_obj() # Call object to run primary pipeline which will output a 4 dim numpy array. 
"""