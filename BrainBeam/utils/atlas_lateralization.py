#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: altas_lateralization.py
Description: Includes functions for taking a directory of images from Allen Institute Reference Atlas and determining where the midline is located.  
Author: David Estrin
Date: 2024-11-19
Version: 1.0
Usage: 
"""
import os, glob
import numpy as np
from skimage.io import imread
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import argparse
import tqdm
from joblib import Parallel, delayed
import pickle
import ipdb

def find_midline_plane(atlas_path, default_region_keys=[672,749,1089]):
    """ Find mindline plane -- This method utalizes a few key brain regions to 
    find the midline of the sample. This midline plane will be used to determine whether
    cell counts are on the ipsilateral or contra lateral side of an injection.
    
    The default key brain regions are: (1) Caudoputamen, (2) Hippocampus, and (3) Ventral Tegmental Area"""
    
    if len(default_region_keys)<3:
        raise("The default number of regions needed to find a plane is 3. Please check number of default region keys")

    # Find plane coordinates:
    # Loop over atlas images and find all pixels associated with region of interest
    # Take the average of X, y and z of pixels to get average coordinate

    # Find and sort atlas images
    def extract_number(file_path):
        filename = os.path.basename(file_path)
        return int(os.path.splitext(filename)[0])
    
    def check_filesizes(file_list):
        for i,file in enumerate(file_list):
            sizoh=np.round(os.path.getsize(file)/1000000)
            if i==0:
                original_size=sizoh
            else:
                if sizoh != original_size:
                    print(f'sizoh change {sizoh}')
                    original_size=sizoh
            
    atlas_images=glob.glob(os.path.join(atlas_path,'*.tiff*')) # Get all atlas images
    atlas_images=sorted(atlas_images,key=extract_number)
    check_filesizes(atlas_images)

    def match_region_to_image(atlas_image,region):
        # Open up image
        try:
            atlas_im_oh = imread(atlas_image)
        except:
            return None
        
        # Get Z level number
        Zlevel,_=os.path.basename(atlas_image).split('.t')
        Zlevel=int(Zlevel)

        # Find X and Y coordinates
        image_oh=np.array(atlas_im_oh)
        coordinates_oh=np.asarray(np.where(image_oh==region))

        if coordinates_oh.size!=0:
            # Get average X and Y coordinate
            coordinates_oh=coordinates_oh.mean(axis=1)

            # Output coordinates and region
            return [int(np.round(coordinates_oh[0])), int(np.round(coordinates_oh[1])), Zlevel, region]

    plane_coordinates = Parallel(n_jobs=-1)(delayed(match_region_to_image)(atlas_image_path,region) for region in default_region_keys for atlas_image_path in tqdm.tqdm(atlas_images))
    filtered_list = [item for item in plane_coordinates if item is not None]
    filtered_list = np.asarray(filtered_list)

    # Extract the unique values in the 4th column
    unique_values = np.unique(filtered_list[:, 3])

    # Compute the average of columns 1-3 for each unique value in column 4
    averages = []
    vals=[]
    for value in unique_values:
        rows = filtered_list[filtered_list[:, 3] == value]  # Filter rows with the specific value in the 4th column
        avg = rows[:, :3].mean(axis=0)    # Compute mean of columns 1-3
        averages.append(avg)
        vals.append(value)
    
    plane_coordinates=np.asarray(averages)

    # Calculate plane coeffs
    vector1 = plane_coordinates[1] - plane_coordinates[0]
    vector2 = plane_coordinates[2] - plane_coordinates[0]
    normal = np.cross(vector1, vector2)
    a,b,c = normal
    d = -np.dot(normal,plane_coordinates[0])
    return a,b,c,d,plane_coordinates

def cell_lateralization(plane_coordinates, plane_coeffs, cell_coordinate):
    """ Using cell coordinate and plane coordinates, 
    determine which side cell is located on """
    coordinate_oh = np.array([cell_coordinate[0], cell_coordinate[1], cell_coordinate[2]])
    vector_oh = coordinate_oh - plane_coordinates[0]
    dp_oh = np.dot(plane_coeffs, vector_oh)

    # Return lateralization of specific cell
    if dp_oh > 0:
        return 'ipsilateral'
    elif dp_oh < 0:
        return 'contralateral'
    elif dp_oh==0:
        return 'midline'

def visualize_atlas_plane(atlas_image_directory, OutputDir, coeffs_oh, skip_factor_oh=50):
    """
    Inputs:
    atlas_image_directory -- (str) The directory containing atlas images that are in tiff format.
    coeffs_oh -- (list) Contains coefficeints for calculating midline plane 
    skip_factor_oh -- (int) The number of pixels to downsample atlas by. 
        Ex. if 50, every 50th pixel will be collected, skipping over 49 pixels
    output_file_fullpath -- (str) The full path to drop the output image

    Outputs:
    This function will save an image as well as matplotlib file which will contain the atlas and plane. 
    """
    def downsample(image_stack,skip_factor):
        """ Re-sample an image stack given a skip factor """
        z_skip=0
        downsampled=[]
        for image in tqdm.tqdm(image_stack):
            if z_skip%skip_factor==0:
                image_oh=np.array(imread(image))
                image_oh=image_oh[::skip_factor,::skip_factor]
                downsampled.append(image_oh)
              
            z_skip+=1
        
        downsampled=np.asarray(downsampled)
        return downsampled
    
    def reassign_atlas_keys(atlas_stack):
        """ Loop over atlas stack and re-assign atlas values to new atlas keys """
        atlas_stack_copy=np.copy(atlas_stack)
        current_color_code=0
        for region in np.unique(atlas_stack):
            atlas_stack_copy[np.where(atlas_stack==region)]=current_color_code
            current_color_code+=1
        
        return atlas_stack_copy

    def plot_stack(atlas_array):
        # Generate 3d plot
        fig = plt.figure(figsize=(20, 20))
        ax = fig.add_subplot(111, projection='3d')

        # Plot atlas
        z_indices, y_indices, x_indices = np.where(atlas_array > 0)
        colors = atlas_array[z_indices, y_indices, x_indices] / atlas_array.max() # 
        ax.scatter(x_indices, y_indices, z_indices, c=colors, cmap='viridis', alpha=0.6, s=5)

        # Labels 
        ax.set_xlabel("Anterior to Posterior")
        ax.set_ylabel("Lateral to Medial to Lateral")
        ax.set_zlabel("Dorsal to Ventral")
        ax.set_title("Registered Allen Reference Atlas")
        ax.view_init(elev=-125, azim=152)  # Elevation & Azimuth
        return fig, ax
    
    def plot_plane(ax,coeffs,atlas_shape,skip_factor):
        # Plot the plane
        aa,bb,cc,dd=coeffs

        aa=aa/skip_factor
        bb=bb/skip_factor
        cc=cc/skip_factor
        dd=dd/skip_factor

        x_range = np.arange(atlas_shape[0])
        y_range = np.arange(atlas_shape[1])
     
        # Create a grid for plotting
        xx, yy = np.meshgrid(x_range, y_range)

        # Solve for z on the plane: z = (-a*x - b*y - d) / c
        zz = (-aa * xx - bb * yy - dd) / cc

        # Clip z values to be within the atlas dimensions
        zz_clipped = np.clip(zz, 15, atlas_shape[2] - 15)
        ax.plot_surface(xx, yy, zz_clipped, alpha=0.5, color='cyan', edgecolor='none')
        return ax

    def extract_number(file_path):
        filename = os.path.basename(file_path)
        return int(os.path.splitext(filename)[0])
    
    # Get image stack
    print('Finding Images ...')
    atlas_images = glob.glob(os.path.join(atlas_image_directory,'*.tiff*')) # Get all atlas images
    atlas_images=sorted(atlas_images,key=extract_number)

    # Downsample Image stack
    print('Downsampling image stack ...')
    atlas_ds = downsample(image_stack=atlas_images,skip_factor=skip_factor_oh)

    # Re-assign atlas keys to new keys
    print('Re-assigning atlas keys ...')
    atlas_ds_new = reassign_atlas_keys(atlas_stack=atlas_ds)

    r1=np.asarray(np.where(atlas_ds==672)).mean(axis=1)
    r2=np.asarray(np.where(atlas_ds==507)).mean(axis=1)
    r3=np.asarray(np.where(atlas_ds==844)).mean(axis=1)
    r4=np.asarray(np.where(atlas_ds==749)).mean(axis=1) 
    r5=np.asarray(np.where(atlas_ds==192)).mean(axis=1) 
    r6=np.asarray(np.where(atlas_ds==797)).mean(axis=1) 
    points = np.asarray([r1,r2,r3,r4,r5,r6])
    points = points[~np.isnan(points).any(axis=1)]

    ipdb.set_trace()

     # Calculate the centroid of the points
    centroid = np.mean(points, axis=0)

    # Center the points around the centroid
    centered_points = points - centroid

    # Perform Singular Value Decomposition
    _, _, vh = np.linalg.svd(centered_points)

    # The normal vector of the plane is the last row of vh (right singular vectors)
    normal = vh[-1]

    # vector1 = hippo - caud
    # vector2 = vent - caud
    # normal = np.cross(vector1, vector2)
    a,b,c = normal
    d = -np.dot(normal,centroid)
    coeffs_oh=[a,b,c,d]

    # Plot Image stack
    print('Plotting Image Stack ...')
    fig_oh, ax_oh = plot_stack(atlas_array=atlas_ds_new)

    # Plot Plane
    print('Plotting Image Stack with Midline plane ...')
    ax_oh = plot_plane(ax=ax_oh,coeffs=coeffs_oh, atlas_shape=atlas_ds_new.shape, skip_factor=50)
    
    # Save the Figure as jpg and fig file
    print('Saving figure in jpg and pkl formats...')
    plt.savefig(os.path.join(OutputDir,'AtlasWithPlane.jpg'))

    with open(os.path.join(OutputDir,'AtlasWithPlane.pkl'), "wb") as f:
        pickle.dump(fig_oh, f)

    print('Completed ... ')
    return


def main(atlas_path_oh, OutputPath):
    if os.path.isfile(os.path.join(OutputPath,"planedata.pkl")):
        print('Loading pkl file containing plane data ...')
        with open(os.path.join(OutputPath,"planedata.pkl"), "rb") as f:
            loaded_list = pickle.load(f)
        a,b,c,d,coordinates_oh=loaded_list
        
    else:
        print('Calculating plane data...')
        a, b, c, d, coordinates_oh = find_midline_plane(atlas_path=atlas_path_oh)

        # Example list
        saved_list = [a,b,c,d,coordinates_oh]

        # Save the list to a file
        with open(os.path.join(OutputPath,"planedata.pkl"), "wb") as f:
            pickle.dump(saved_list, f)

    # test_cell1=np.array([500,1000,500])
    # test_res1 = cell_lateralization(coordinates_oh,a,b,c,d,test_cell1)
    # print(f'Test cell 1 is located {test_res1}')

    # test_cell2=np.array([500,1000,500])
    # test_res2 = cell_lateralization(coordinates_oh,a,b,c,d,test_cell2)
    # print(f'Test cell 2 is located {test_res2}')

    # test_cell3=np.array([500,1000,500])
    # test_res3 = cell_lateralization(coordinates_oh,a,b,c,d,test_cell3)
    # print(f'Test cell 3 is located {test_res3}')

    visualize_atlas_plane(atlas_image_directory=atlas_path_oh, OutputDir=OutputPath, coeffs_oh=[a,b,c,d], skip_factor_oh=50)

def cli_parser():
    """ Parse command line arguments """
    parser=argparse.ArgumentParser()
    parser.add_argument('--atlas_path',type=str, required=True)
    parser.add_argument('--output_path',type=str,required=True)
    args=parser.parse_args()

    # Generate output path if it does not exist
    if not os.path.exists(args.output_path):
        os.mkdir(args.output_path)

    return args

def load_fig(fig):
    with open(r"C:\Users\listo\tempdrop\AtlasWithPlane.pkl") as f: 
        loaded_fig=pickle.load(f) 

if __name__=='__main__':
    args=cli_parser()
    main(atlas_path_oh=args.atlas_path,OutputPath=args.output_path)