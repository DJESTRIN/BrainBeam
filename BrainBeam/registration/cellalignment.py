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
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
import scipy.ndimage
from skimage.morphology import dilation, disk
import ipdb
import os, glob
import pickle
from scipy.spatial.distance import cdist
import itertools
import argparse
from BrainBeam.registration.padding import zero_pad_arrays
from BrainBeam.registration.transforms import *
from BrainBeam.registration.graphics import slice_views, overlay_masks, volume_graphics

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


def atlas_cell_3d_plot(atlas,cell_mask,file, downsample_factor=4):
    matplotlib.use("tkagg")
    cell_mask = cell_mask[::-1,:,:]
    mask_coordinates = np.where(cell_mask>0)
    atlas_downsampled = atlas[::downsample_factor, ::downsample_factor, ::downsample_factor]
    coords = np.array(np.where(atlas_downsampled>1)).T 

    values = atlas_downsampled[coords[:, 0], coords[:, 1], coords[:, 2]]
    unique_values = np.unique(values)

    # Assign each unique key a unique color
    num_colors = len(unique_values)
    color_map = plt.get_cmap('tab10', num_colors)  # Pick a colormap with discrete colors
    color_dict = {val: color_map(i) for i, val in enumerate(unique_values)}  # Map keys to colors

    # Create a color array
    colors = np.array([color_dict[val] for val in values])

    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111, projection='3d')
    ax.scatter(coords[:, 0], coords[:, 1], coords[:, 2], c=colors, alpha=0.05)
    ax.scatter(mask_coordinates[0]/downsample_factor,
               mask_coordinates[1]/downsample_factor,
               mask_coordinates[2]/downsample_factor, 
               color='red')
    plt.savefig(file, dpi=300) 
    print('saved voxel image')
    plt.show()
    return 


def slide_atlas_plot(atlas, cell_mask):
    # Ensure TkAgg is used
    matplotlib.use("tkagg")
    # Extract coordinates and values, filtering out zero or unwanted points
    valid_mask = atlas > 1  # Only include values greater than 1
    coords = np.array(np.where(valid_mask)).T  # [z, y, x] format
    values = atlas[valid_mask]  # Get corresponding values

    unique_values, inverse_indices = np.unique(values, return_inverse=True)  # Get unique mapping
    num_colors = len(unique_values)

    # Use a perceptually uniform colormap with more distinct colors
    color_map = plt.get_cmap('rainbow', num_colors)  # Alternatives: 'turbo', 'tab20'
    colors = color_map(inverse_indices)  # Assign colors based on index

    mask_coordinates = np.array(np.where(cell_mask > 0)).T

    # Create figure
    fig, ax = plt.subplots(figsize=(6, 6))
    plt.subplots_adjust(bottom=0.25)  # Space for slider

    # Initial slice setup
    initial_slice = atlas.shape[2] // 2
    slice_mask = coords[:, 2] == initial_slice  # Select only points in the initial slice
    cell_slice_mask = mask_coordinates[:, 2] == initial_slice

    sc = ax.scatter(coords[slice_mask, 0], coords[slice_mask, 1], c=colors[slice_mask], s=10)
    sc_mask = ax.scatter(mask_coordinates[cell_slice_mask, 0], 
                        mask_coordinates[cell_slice_mask, 1], 
                        marker="^", facecolors='red', edgecolors='black', 
                        linewidth=1.5, s=50)

    ax.set_xlim([0, atlas.shape[0]])
    ax.set_ylim([0, atlas.shape[1]])
    ax.set_title(f'Slice {initial_slice}')

    # Add slider for scrolling through slices
    ax_slider = plt.axes([0.25, 0.1, 0.5, 0.03])
    slider = Slider(ax_slider, 'Slice', 0, atlas.shape[2] - 1, valinit=initial_slice, valstep=1)

    # Update function for the slider
    def update(val):
        slice_idx = int(slider.val)
        
        slice_mask = coords[:, 2] == slice_idx  # Select new atlas slice points
        cell_slice_mask = mask_coordinates[:, 2] == slice_idx  # Select new cell slice points
        
        if np.any(slice_mask):
            sc.set_offsets(coords[slice_mask, :2])
            sc.set_color(colors[slice_mask])
        else:
            sc.set_offsets([])

        if np.any(cell_slice_mask):
            sc_mask.set_offsets(mask_coordinates[cell_slice_mask, :2])
        else:
            sc_mask.set_offsets([])

        ax.set_title(f'Slice {slice_idx}')
        fig.canvas.draw_idle()

    slider.on_changed(update)

    plt.show()



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
                 force_orientations,
                 force_flips,
                 cell_count_files = None,):
        self.zp_id_atlas = zp_id_atlas
        self.zp_template_atlas = zp_template_atlas
        self.ds_zp_transformed_moving_image = ds_zp_transformed_moving_image
        self.drop_path = drop_path # Path containing pkl transformation files
        self.cell_count_files = cell_count_files
        self.force_orientations = force_orientations
        self.force_flips = force_flips


        if self.cell_count_files:
            self.skip_flag = False

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

        self.channel_name = []
    
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

        self.plot_original_overlay()

        # Grab alignment file(s) data
        self.gather_transformations()

        # Apply transform(s) to aggregate mask
        self.transform_cell_mask()

        # Crop all data to atlas bounding box
        self.crop_by_bounding()

        # Graph results 
        if self.transformed_volumes:
            for mask_oh, name_oh in zip(self.transformed_volumes,self.channel_name):
                overlay_masks(atlas = self.zp_id_atlas,
                            image = self.ds_zp_transformed_moving_image,
                            mask = mask_oh,
                            output_filename=os.path.join(self.drop_path,f"atlas_image_cellcount_overlay_{name_oh}.jpg"),
                            atlas_categorical=True)
                print(f'output jpg file to {self.drop_path}')

                # atlas_cell_3d_plot(atlas = self.zp_id_atlas, 
                #                    cell_mask = mask_oh,
                #                    file=os.path.join(self.drop_path,f"atlas_view_{name_oh}.jpg"))
                
                slide_atlas_plot(atlas = self.zp_id_atlas,
                                cell_mask = mask_oh)

        # Generate the 4-D array
        self.generate_4D_array()
        
    def plot_original_overlay(self):
        original_array = np.load(os.path.join(self.drop_path,"downsampled_volume.npy"))
        slice_views(array1=self.coordinate_mask_all[0],
                    array2=original_array,
                    output_filename=os.path.join(self.drop_path,"original_overlay.jpg"))

    def read_cell_count_file(self):
        """ Convert cell count files into numpy array attributes for class. 
            Eliminates double counts as well. """
        if len(self.cell_count_files)>0: # Are count files provided
            
            self.channel_name=[] 
            self.cell_coordinates=[]
            for file in self.cell_count_files:
                # Determine channel name
                if '488' in file:
                    self.channel_name.append('488')
                elif '561' in file:
                    self.channel_name.append('561')
                elif '647' in file:
                    self.channel_name.append('647')
                elif '785' in file:
                    self.channel_name.append('785')

                # Load in counts, arranges axes and eliminate double counts
                counts_oh = pd.read_csv(file).to_numpy()
                counts_oh = counts_oh[:, [1, 0, 2]] # May need to re-orient axis....?
                counts_oh[:, 2] = counts_oh[::-1, 2]
                
                counts_oh = determine_doublecount_points(array1=counts_oh, array2=counts_oh)
                self.cell_coordinates.append(counts_oh)

        else: # No count csv files provided
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
                x, y, z = (cell - 1)   ##### This -1 should be deleted?
                self.coordinate_mask_oh[x, y, z] += 1
            
            # Append numpy array to list
            self.coordinate_mask_all.append(self.coordinate_mask_oh)

    def gather_transformations(self):
        """ Through self.drop_dir, code will find all transform files, open them and save as attributes for nonrigid and rigid seperately.
            Files must end with an integer or will not be included. Integer is strictly for determining order of application to image volumes."""
        
        def transform_sort(full_file_path):
            nameoh = full_file_path.split('_')[-1]
            return int(nameoh.split('.')[0].split('tep')[1])

        # get rigid transformations including stretching
        rigid_transform_files = sorted(glob.glob(os.path.join(self.drop_path,"rigid*.pkl")), key=transform_sort)
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
        self.nonrigid_transform_files =  sorted(glob.glob(os.path.join(self.drop_path,"*nonrigid*.pkl")), key=transform_sort)
        self.nonrigid_transforms = []
        for file in self.nonrigid_transform_files:
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

            # counts to brain transpose    
            transformed_mask = np.transpose(transformed_mask,(2,1,0))

            if self.force_orientations is not None:
                transformed_mask = np.transpose(transformed_mask,
                                                (self.force_orientations[0],
                                                 self.force_orientations[1],
                                                 self.force_orientations[2])) # brain to atlas transpose
            if self.force_flips is not None:
                transformed_mask = transformed_mask[::self.force_flips[0], 
                                                    ::self.force_flips[1], 
                                                    ::self.force_flips[2]]  # Flip if needed

            # Add zero padding to aggregate mask
            template_array = np.zeros((self.new_x_pad_dim, self.new_y_pad_dim, self.new_z_pad_dim))
            transformed_mask, _ = zero_pad_arrays(array1=transformed_mask, array2=template_array)
            print(f'Pretrasnformation cell count: {maskoh.sum()}')

            # Perform rigid transformations
            for transform_oh, transform_type in zip(self.rigid_transforms,self.rigid_transform_types):
                if transform_type==0:
                    transformed_mask = rigid_transform(best_params = transform_oh,
                                                       moving_image = sitk.GetImageFromArray(transformed_mask), 
                                                       fixed_image = sitk.GetImageFromArray(self.zp_template_atlas.astype(np.float32)))
                elif transform_type==1:
                    transformed_mask = stretch_transform(best_params = transform_oh, 
                                                         moving_image = sitk.GetImageFromArray(transformed_mask), 
                                                         fixed_image = sitk.GetImageFromArray(self.zp_template_atlas.astype(np.float32)))
                else:
                    raise("Transform type should be either 0 or 1. Other type given")
                
            # Perform Non Rigid transformation(s)
            print(f'Post rigid transformation cell count: {transformed_mask.sum()}')
            final_nonrigid_transform_oh = self.nonrigid_transforms[-1]
            transformed_mask = nonrigid_transform(best_params = final_nonrigid_transform_oh,
                                                  moving_image = sitk.GetImageFromArray(transformed_mask),
                                                  fixed_image = sitk.GetImageFromArray(self.zp_template_atlas.astype(np.float32)))
            print(f'Post non-rigid transformation cell count: {transformed_mask.sum()}')
           
            # Remove cell counts outside atlas
            # transformed_mask[self.zp_id_atlas==0] *= 0
            print(f'Post atlas crop cell count: {transformed_mask.sum()}')

            # Append mask to list
            self.transformed_volumes.append(transformed_mask)

    def crop_by_bounding(self):
        print("Cropping final data by bounding box. ")
        # Get bounding box of the id image
        nonzero_coordinates = np.where(self.zp_id_atlas>0)
        mins_oh = [nonzero_coordinates[0].min(), nonzero_coordinates[1].min(), nonzero_coordinates[2].min()]
        maxs_oh = [nonzero_coordinates[0].max(), nonzero_coordinates[1].max(), nonzero_coordinates[2].max()]

        # Crop all data
        self.zp_id_atlas = self.zp_id_atlas[mins_oh[0]:maxs_oh[0],
                                            mins_oh[1]:maxs_oh[1],
                                            mins_oh[2]:maxs_oh[2]]
        
        self.zp_template_atlas = self.zp_template_atlas[mins_oh[0]:maxs_oh[0],
                                            mins_oh[1]:maxs_oh[1],
                                            mins_oh[2]:maxs_oh[2]]
        
        self.ds_zp_transformed_moving_image = self.ds_zp_transformed_moving_image[mins_oh[0]:maxs_oh[0],
                                            mins_oh[1]:maxs_oh[1],
                                            mins_oh[2]:maxs_oh[2]]
        
        if self.transformed_volumes:
            transformed_volumes_cropped = []
            for mask in self.transformed_volumes:
                mask = mask[mins_oh[0]:maxs_oh[0],
                            mins_oh[1]:maxs_oh[1],
                            mins_oh[2]:maxs_oh[2]]
                transformed_volumes_cropped.append(mask)
            
            self.transformed_volumes = transformed_volumes_cropped

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
            volumeoh = np.array(cell_list)
            mapped_array =  np.concatenate((mapped_array, volumeoh[...,np.newaxis]), axis=3)

        # Save data into numpy file 
        self.mapped_array = mapped_array
        np.save(os.path.join(self.drop_path,'mapped_array.npy'), self.mapped_array) 

        self.channel_name = np.asarray(self.channel_name)
        np.save(os.path.join(self.drop_path,'channel_names.npy'), self.channel_name) 

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
    
    cellobj.update_coordinate_systems(new_x_dim = ds_zp_transformed_moving_image.shape[0], 
                                      new_y_dim = ds_zp_transformed_moving_image.shape[1], 
                                      new_z_dim = ds_zp_transformed_moving_image.shape[2], 
                                      original_x_dim = 10000, # random number
                                      original_y_dim = 9000,  # random number
                                      original_z_dim = 4000) # random number
    
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

# & C:/Users/listo/AppData/Local/anaconda3/envs/registration/python.exe c:/Users/listo/BrainBeam/BrainBeam/registration/cellalignment.py --zp_id_atlas_file C:\Users\listo\example_registration_data\sub2_output\current_run_2025_02_02_20_10_17\target_array.npy --zp_template_atlas_file C:\Users\listo\example_registration_data\sub2_output\current_run_2025_02_02_20_10_17\target_array.npy --ds_zp_transformed_moving_image_file C:\Users\listo\example_registration_data\sub2_output\current_run_2025_02_02_20_10_17\nonrigid_moving_image.npy --drop_path C:\Users\listo\example_registration_data\sub2_output\current_run_2025_02_02_20_10_17 --cell_count_files C:\Users\listo\example_registration_data\sub2_output\current_run_2025_02_02_20_10_17\cage4467200_animal04_channel561_cell_counts.csv C:\Users\listo\example_registration_data\sub2_output\current_run_2025_02_02_20_10_17\cage4467200_animal04_channel647_cell_counts.csv 