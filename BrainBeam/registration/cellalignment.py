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
import os

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
    def __init__(self, cell_count_files = None):
        self.cell_count_files = cell_count_files

        self.new_x_dim = None
        self.new_y_dim = None
        self.new_z_dim = None
        self.original_x_dim = None
        self.original_y_dim = None
        self.original_z_dim = None
    
    def update_coordinate_systems(self,new_x_dim, new_y_dim, new_z_dim, original_x_dim,original_y_dim,original_z_dim):
        # Set dimensions for new and original arrays for reference by code
        self.new_x_dim = new_x_dim
        self.new_y_dim = new_y_dim
        self.new_z_dim = new_z_dim
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
                if ds_x>self.moving_image.shape[0]:
                    ds_x=int(self.moving_image.shape[0])

                if ds_y>self.moving_image.shape[1]:
                    ds_y=int(self.moving_image.shape[1])

                if ds_z>self.moving_image.shape[2]:
                    ds_z=int(self.moving_image.shape[2])

                # Append new coordinates to the list
                self.ds_cell_coordinates.append([ds_x, ds_y, ds_z])

            # Convert to a numpy array and make sure no values are greater then dims
            self.ds_cell_coordinates_all.append(np.asarray(self.ds_cell_coordinates))

    def cell_coordinates_to_aggregate_mask(self):
        # Generate 3D array of zeros
        self.coordinate_mask = np.zeros(self.moving_image.shape, dtype=int)

        # Aggregate total number of cells per voxel in 3d mask
        for cell in self.ds_cell_coordinates:
            x, y, z = cell
            self.coordinate_mask[x, y, z] += 1

    def transform_cell_mask(self):
        #
        transformed_mask = self.coordinate_mask.copy()

        # Add zero padding 

        # Perform Rigid transformation

        # Perform Non Rigid transformation(s)
    
    def save_final_array(self):
        """ Save the final array (4D) where 3D are Height, Width, Depth
            4th D is:
            Atlas image -- the acutal ARA
            Template image --  orignal template image from ARA
            Moving image -- Transformed raw data image
            Aggregate Cell Count Mask -- the mask containing values [0-inf) for number of cells in voxel. 

            Output will be a numpy array 
            """

        # Put all relevant arrays into a single array
        mapped_array = np.stack([self.atlas_array, self.template_array, self.moving_array, self.transformed_mask], axis=3)

        # Crop out all zero padding for ease of use
        non_zero_x = np.any(mapped_array != 0, axis=(1, 2, 3))  # Collapse y, z, 4th D
        non_zero_y = np.any(mapped_array != 0, axis=(0, 2, 3))  # Collapse x, z, 4th D
        non_zero_z = np.any(mapped_array != 0, axis=(0, 1, 3))  # Collapse x, y, 4th D
        x_min, x_max = np.where(non_zero_x)[0][[0, -1]]
        y_min, y_max = np.where(non_zero_y)[0][[0, -1]]
        z_min, z_max = np.where(non_zero_z)[0][[0, -1]]

        # Slice the array to crop out unnecessary zeros
        self.cropped_mapped_array = mapped_array[x_min:x_max+1, y_min:y_max+1, z_min:z_max+1, :]
        np.save(os.path.join(self.drop_path,'cropped_mapped_array.npy'), self.mapped_array_cropped ) 
            
if __name__=='__main__':
    extended_main()

"""
Example call 

& C:/Users/listo/AppData/Local/anaconda3/envs/registration/python.exe c:/Users/listo/BrainBeam/BrainBeam/cust_registration/cellalignment.py 
--image_path c:/Users/listo/example_registration_data/sub1 
--atlas_path c:/Users/listo/example_registration_data/atlas 
--output_path c:/Users/listo/example_registration_data/sub1_outputs 
--cell_counts c:/Users/listo/example_registration_data/cellcount/cell_counts.csv


"""