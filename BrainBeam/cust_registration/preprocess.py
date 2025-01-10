#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: preprocess.py
Description: Contains code for preprocessing images for registration
Author: David Estrin
Date: 2024-12-20
Version: 1.0
"""
import numpy as np
from scipy.ndimage import gaussian_filter
from BrainBeam.cust_registration.graphics import slice_views
from BrainBeam.cust_registration.padding import zero_pad_arrays
import ipdb

def replace_signal(volume,threshold=95, cube_size=9):
    """
    
    """
    # plot original volume
    slice_views(array=(volume/2),output_filename='presignalextract.jpg')

    # Threshold the data
    non_zero_array = volume[volume != 0]
    threshold_value = np.percentile(non_zero_array, threshold)
    signal_points = np.where(volume>=threshold_value)

    # Replace these signal points with nan
    volume[signal_points] = np.nan

    # Zero pad the volume
    new_shape = np.array(volume.shape) + (cube_size*2)
    empty_array = np.zeros(tuple(new_shape))
    volume_padded, _ = zero_pad_arrays(array1=volume,array2=empty_array)
    del empty_array

    # reshape signal point
    signal_points = np.array(signal_points).T + cube_size # reshape and make array

    # Create a weighted matrix
    x, y, z = np.indices((cube_size, cube_size, cube_size))
    center = (cube_size - 1) / 2
    distances = np.maximum.reduce([np.abs(x - center), np.abs(y - center), np.abs(z - center)])
    values = cube_size - distances
    weighted_matrix = values.astype(int) 

    # Calculate weighted average value for local data surrounding point
    new_values =[]
    for point in signal_points:
        local_data = volume_padded[point[0]-(cube_size // 2):point[0]+(cube_size // 2) + 1,
                            point[1]-(cube_size // 2):point[1]+(cube_size // 2) + 1,
                            point[2]-(cube_size // 2):point[2]+(cube_size // 2) + 1]
        
        # Calculate weighted average
        weighted_average_value = np.nansum(local_data*weighted_matrix)/weighted_matrix.sum()
        new_values.append(weighted_average_value)

    # Replace original point data with the weighted average value
    for weighted_average_value,point in zip(new_values,signal_points):
        volume_padded[point[0],point[1],point[2]] = weighted_average_value
        
    # remove zero padding
    volume = volume_padded[cube_size:-cube_size,cube_size:-cube_size,cube_size:-cube_size]
    slice_views(array=(volume/2),output_filename='postsignalextract.jpg')
    return volume 

def blur(volume, sigma=2):
    return gaussian_filter(volume, sigma=sigma)

def preprocess(volume):
    """ general pipeline for preprocessing for the registration process """
    volume = replace_signal(volume)
    volume = blur(volume)
    return volume

if __name__=='__main__':
    file=r'C:\Users\listo\example_registration_data\sub1_output\current_run_2025_01_09_22_33_11\downsampled_volume.npy'
    volume_test = np.load(file)
    desig_volume = replace_signal(volume=volume_test)