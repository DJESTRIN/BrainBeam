#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: padding.py
Description: pads 3d arrays to match in size
Author: David Estrin
Date: 2024-12-20
Version: 1.0
"""

import numpy as np

# Function to calculate padding for an array
def calculate_padding(array, target_shape):
    pad_x = target_shape[0] - array.shape[0]
    pad_y = target_shape[1] - array.shape[1]
    pad_z = target_shape[2] - array.shape[2]

    pad_x_before = pad_x // 2
    pad_x_after = pad_x - pad_x_before
    pad_y_before = pad_y // 2
    pad_y_after = pad_y - pad_y_before
    pad_z_before = pad_z // 2
    pad_z_after = pad_z - pad_z_before

    return ((pad_x_before, pad_x_after), 
            (pad_y_before, pad_y_after), 
            (pad_z_before, pad_z_after))

def zero_pad_arrays(array1,array2):
    max_x = max(array1.shape[0], array2.shape[0])
    max_y = max(array1.shape[1], array2.shape[1])
    max_z = max(array1.shape[2], array2.shape[2])   

    target_shape = (max_x, max_y, max_z)

    padding1 = calculate_padding(array1, target_shape)
    padding2 = calculate_padding(array2, target_shape)

    padded_array1 = np.pad(array1, padding1, mode='constant', constant_values=0)
    padded_array2 = np.pad(array2, padding2, mode='constant', constant_values=0)
    return padded_array1, padded_array2
