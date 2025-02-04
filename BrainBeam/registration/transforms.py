#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: transforms.py
Description: Functions for applying rigid, nonrigid and stretch transforms to an input volume
Author: David Estrin
Date: 2025-01-14
Version: 1.0
"""
import SimpleITK as sitk
import numpy as np
from BrainBeam.registration.bayessearch import set_affine_rotation, adjust_volume_shape
from scipy.ndimage import zoom

def rigid_transform(best_params, moving_image, fixed_image):
    """ Given the best parameters, this will perform a rigid transformation """
    # Set up affine transform
    best_affine_transform = sitk.AffineTransform(3)
    best_affine_transform = set_affine_rotation(best_affine_transform, best_params['theta_x'], best_params['theta_y'], best_params['theta_z'])
    best_affine_transform.SetTranslation([best_params['translation_x'], best_params['translation_y'], best_params['translation_z']])
    best_affine_transform.Scale(best_params['scale'])

    # Resample the moving image with the best transform
    best_resampler = sitk.ResampleImageFilter()
    best_resampler.SetSize(fixed_image.GetSize())
    best_resampler.SetOutputSpacing(fixed_image.GetSpacing())
    best_resampler.SetTransform(best_affine_transform)
    best_resampler.SetInterpolator(sitk.sitkNearestNeighbor)
    best_aligned_image = best_resampler.Execute(moving_image)

    # Convert back to numpy
    aligned_array = sitk.GetArrayFromImage(best_aligned_image)
    return aligned_array

def stretch_transform(best_params, moving_image, fixed_image):
    """ Given the best parameters, this will perform a stretch transformation """
    # Convert to numpy
    moving_image = sitk.GetArrayFromImage(moving_image)
    fixed_image = sitk.GetArrayFromImage(fixed_image)

    # Rescale moving image so bounding boxes align
    moving_image = zoom(moving_image, best_params, order=1)

    # Resample moving image so its shape is the same as when it started
    aligned_array = adjust_volume_shape(volume=moving_image,target_shape=fixed_image.shape)
    return aligned_array

def nonrigid_transform(best_params, moving_image, fixed_image):
    """ Given the best parameters, this will perform a non rigid transformation """
    moving_image = sitk.Resample(moving_image, fixed_image, best_params, sitk.sitkNearestNeighbor, 0.0, moving_image.GetPixelID())
    aligned_array = sitk.GetArrayFromImage(moving_image)
    return aligned_array


