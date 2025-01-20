#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: cellalignment.py
Description: 
Author: David Estrin
Date: 2024-12-11
Version: 1.0
"""

# Load dependencies
import pandas as pd
import numpy as np
import ipdb
import os, glob
import pickle
from scipy.spatial.distance import cdist
import itertools
import argparse
from BrainBeam.registration.padding import zero_pad_arrays
from BrainBeam.registration.transforms import *

# Custom classes and functions
def determine_doublecount_points(array1, array2, threshold=5):
    combined_array = np.vstack((array1, array2))
    distances = cdist(combined_array, combined_array, metric='euclidean')
    within_threshold = (distances < threshold) & ~np.eye(combined_array.shape[0], dtype=bool)
    
    to_remove = set()
    for i in range(within_threshold.shape[0]):
        if i not in to_remove:
            close_points = np.where(within_threshold[i])[0]
            to_remove.update(close_points)
    
    to_remove = sorted(to_remove)
    final_array = np.delete(combined_array, to_remove, axis=0)
    return final_array

def determine_coexpressing_points(array1, array2, threshold=5):
    distances = cdist(array1, array2, metric='euclidean')
    within_threshold = np.where(distances < threshold)
    overlapping_points = np.concatenate((array1[within_threshold[0]], array2[within_threshold[1]]), axis=0)
    unique_overlapping_points = np.unique(overlapping_points, axis=0)
    return unique_overlapping_points

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
        # Load in cell coordinates for all files and eliminate double counts
        self.read_cell_count_file()

        # Determine coexpression cell locations
        self.determine_coexpression()

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

        # Generate the 4-D array
        self.generate_4D_array()
        
    def read_cell_count_file(self):
        self.cell_coordinates=[]
        if len(self.cell_count_files)==1:
            # Read in data
            counts_oh = pd.read_csv(self.cell_count_files).to_numpy()

            # Eliminate double counts
            counts_oh = determine_doublecount_points(array1=counts_oh, array2=counts_oh)

            # Save to list
            self.cell_coordinates.append(counts_oh)

        elif len(self.cell_count_files)>1:
            for i in range(len(self.cell_count_files)):
              # Read in data
              counts_oh = pd.read_csv(self.cell_count_files[i]).to_numpy()

              # Eliminate double counts
              counts_oh = determine_doublecount_points(array1=counts_oh, array2=counts_oh)

              # Save to list
              self.cell_coordinates.append(counts_oh)

        else:
            self.skip_flag = True
            print('No cell coordinate files provided, so all cell alignment code will be skipped')

    def determine_coexpression(self):
        cell_coordinates_final = self.cell_coordinates
        if len(self.cell_coordinates)>1:
            for cell_list1, cell_list2 in itertools.combinations(self.cell_coordinates, 2):
                coexpressing = determine_coexpressing_points(array1=cell_list1,array2=cell_list2)
                
                # Append the overlapping list as a new array
                if coexpressing.size != 0:
                    cell_coordinates_final.append(coexpressing)
        else:
            print('Only one cell coordinate list provided, nothing to check for coexpression')

        self.cell_coordinates = cell_coordinates_final

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

def cli_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--zp_id_atlas_file', type=str)
    parser.add_argument('--zp_template_atlas_file', type=str)
    parser.add_argument('--ds_zp_transformed_moving_image_file', type=str)
    parser.add_argument('--drop_path', type=str)
    parser.add_argument('--cell_count_files', nargs='*', type=str, default=None)
    args = parser.parse_args()

    if args.cell_count_files:
        cell_count_files = []
        for file in args.cell_count_files:
            cell_count_files.append(file)

    if args.zp_id_atlas_file:
        zp_id_atlas = np.load(args.zp_id_atlas_file)

    if args.zp_template_atlas_file:
        zp_template_atlas = np.load(args.zp_template_atlas_file)

    if args.ds_zp_transformed_moving_image_file:
        ds_zp_transformed_moving_image = np.load(args.ds_zp_transformed_moving_image_file)

    if args.drop_path:
        drop_path = args.drop_path

    return drop_path, cell_count_files, zp_id_atlas, zp_template_atlas, ds_zp_transformed_moving_image

if __name__=='__main__':
    drop_path, cell_count_files, zp_id_atlas, zp_template_atlas, ds_zp_transformed_moving_image = cli_parser()

    cellobj = cellalignment(zp_id_atlas = zp_id_atlas,
                            zp_template_atlas = zp_template_atlas,
                            ds_zp_transformed_moving_image = ds_zp_transformed_moving_image,
                            drop_path = drop_path,
                            cell_count_files = cell_count_files)
    
    ipdb.set_trace()
    cellobj.update_coordinate_systems(new_x_dim = ds_zp_transformed_moving_image.shape[0], 
                                      new_y_dim = ds_zp_transformed_moving_image.shape[1], 
                                      new_z_dim = ds_zp_transformed_moving_image.shape[2], 
                                      original_x_dim = 10000, # random number
                                      original_y_dim = 9000,  # random number
                                      original_z_dim = 4000) # random number
    ipdb.set_trace()
    cellobj()

# --zp_id_atlas_file C:\Users\listo\example_registration_data\sub2_output\current_run_2025_01_14_14_22_16\target_array.npy
# --zp_template_atlas_file C:\Users\listo\example_registration_data\sub2_output\current_run_2025_01_14_14_22_16\target_array.npy
# --ds_zp_transformed_moving_image_file C:\Users\listo\example_registration_data\sub2_output\current_run_2025_01_14_14_22_16\nonrigid_moving_image.npy
# --drop_path C:\Users\listo\example_registration_data\sub2_output\current_run_2025_01_14_14_22_16
# --cell_count_files C:\Users\listo\example_registration_data\cellcount\cell_counts.csv

   

# Here is an example of how this class is meant to be run in the registration script ... 
 
# from BrainBeam.registration.cellalignment import cellalignment # Import package

# cell_alignment_obj = cellalignment(zp_id_atlas, zp_template_atlas, ds_zp_transformed_moving_image, drop_path) # create the object
# cell_alignment_obj.update_coordinate_systems(new_x_dim, new_y_dim, new_z_dim, original_x_dim, original_y_dim, original_z_dim) # add the coordinate system data
# cell_alignment_obj() # Call object to run primary pipeline which will output a 4 dim numpy array. 
