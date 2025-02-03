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
from BrainBeam.registration.graphics import slice_views
from BrainBeam.registration.padding import zero_pad_arrays
from allensdk.core.reference_space_cache import ReferenceSpaceCache
from pathlib import Path

def replace_signal(volume,threshold=99, cube_size=9,normalize=False):
    """ Find high signal points and replace it using a 3D convolutional like filter """
    # normalize data if set
    if normalize:
        volume = ((volume-volume.min())/(volume.max()-volume.min()))*255

    # Threshold the data
    non_zero_array = volume[volume != 0]
    threshold_value = np.percentile(non_zero_array, threshold)
    signal_points = np.where(volume>=threshold_value)
    volume = volume.astype(np.float16)

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

    if normalize:
        volume = ((volume-volume.min())/(volume.max()-volume.min()))*255

    return volume 

def blur(volume, sigma=2):
    return gaussian_filter(volume, sigma=sigma)

def preprocess(volume):
    """ general pipeline for preprocessing for the registration process """
    volume = replace_signal(volume)
    volume = blur(volume)
    return volume

def flatten_list(nested_list):
    flat_list = []
    for item in nested_list:
        if isinstance(item, list):
            flat_list.extend(flatten_list(item))  # Recursively flatten
        else:
            flat_list.append(item)
    return flat_list

if __name__=='__main__':
    atlas_path = r'c:\Users\listo\example_registration_data\atlas'
    reference_space_key = 'average_template/'
    rspc = ReferenceSpaceCache(50, reference_space_key, manifest=Path(atlas_path) / 'manifest.json')
    template, template_meta = rspc.get_template_volume()

    # file=r'C:\Users\listo\example_registration_data\sub1_output\current_run_2025_01_09_22_33_11\downsampled_volume.npy'
    # volume_test = np.load(file)
    # desig_volume = replace_signal(volume=volume_test)
    desig_template = replace_signal(volume = template, normalize=True)