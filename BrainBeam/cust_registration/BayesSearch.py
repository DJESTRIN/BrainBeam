#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: compress_ilastik_output.py
Description: 
Author: David Estrin
Date: 2024-08-28
Version: 1.0
"""
import optuna
import SimpleITK as sitk
import numpy as np
import matplotlib.pyplot as plt
import ipdb
import plotly.graph_objects as go
from datetime import datetime
import os

def print_results_every_n_trials(study, trial, n=10):
    """
    Callback function to print study results every n trials.
    """
    if trial.number % n == 0:
        print(f"Trial {trial.number}: Best Value = {study.best_value:.5f}, Best Params = {study.best_params}")

def compute_mse(fixed_image, moving_image,lambda_overlap=0.5):
    """
    Compute the Mean Squared Error (MSE) between two SimpleITK images.
    """
    fixed_array = sitk.GetArrayFromImage(fixed_image)  # Convert to NumPy array
    moving_array = sitk.GetArrayFromImage(moving_image)  # Convert to NumPy array
    
    # Ensure both arrays are the same size
    assert fixed_array.shape == moving_array.shape, "Images must have the same size for MSE computation."
    
    # Compute overlap as pentalty and mse
    overlap = (fixed_array > 0) & (moving_array > 0)
    overlap_ratio = np.sum(overlap) / np.prod(fixed_array.shape)
    mse = np.mean((fixed_array - moving_array) ** 2)
    penalty = mse + lambda_overlap * (1 - overlap_ratio)
    return penalty

def set_affine_rotation(affine_transform, theta_x, theta_y, theta_z):
    """
    Set rotation for a SimpleITK AffineTransform using rotation angles (in radians) 
    for x, y, and z axes.
    """
    # Compute rotation matrices for each axis
    Rx = np.array([[1, 0, 0],
                   [0, np.cos(theta_x), -np.sin(theta_x)],
                   [0, np.sin(theta_x), np.cos(theta_x)]])
    
    Ry = np.array([[np.cos(theta_y), 0, np.sin(theta_y)],
                   [0, 1, 0],
                   [-np.sin(theta_y), 0, np.cos(theta_y)]])
    
    Rz = np.array([[np.cos(theta_z), -np.sin(theta_z), 0],
                   [np.sin(theta_z), np.cos(theta_z), 0],
                   [0, 0, 1]])

    # Combine rotations: R = Rz * Ry * Rx (order matters)
    R = Rz @ Ry @ Rx  # Matrix multiplication

    # Flatten the rotation matrix and set it in the affine transform
    affine_transform.SetMatrix(R.flatten().tolist())

    return affine_transform

def plot_arrays_3d(array1,array2,array1_thresh,array2_thresh,ds_factor=10):
    # Function to extract coordinates of non-zero values in a 3D array
    def get_nonzero_coordinates(array):
        x, y, z = np.where(array>10)
        return x, y, z
    
    def downsample_coordinates(x, y, z, fraction=0.1):
        """
        Downsample coordinates to a given fraction.
        Args:
            x, y, z: Arrays of coordinates.
            fraction: Fraction of points to keep (0 < fraction <= 1).
        Returns:
            Downsampled x, y, z coordinates.
        """
        total_points = len(x)
        sample_size = int(total_points * fraction)
        indices = np.random.choice(total_points, sample_size, replace=False)
        return x[indices], y[indices], z[indices]

    # Set up array 1 for plotting
    array1ds = array1[::ds_factor, ::ds_factor, ::ds_factor] # downsample

    # Threshold data 
    filtered_array1 = np.copy(array1ds)
    filtered_array1[filtered_array1 < (array1_thresh)] = np.nan  # Masked values as NaN

    # Get coordinates for plotly
    x1, y1, z1 = np.meshgrid(np.arange(filtered_array1.shape[0]),
                        np.arange(filtered_array1.shape[1]),
                        np.arange(filtered_array1.shape[2]),
                        indexing='ij')
    x1_flat = x1.flatten()
    y1_flat = y1.flatten()
    z1_flat = z1.flatten()
    v1_flat = filtered_array1.flatten()

    # Set up array 2
    array2ds = array2[::ds_factor, ::ds_factor, ::ds_factor] # downsample

    # Threshold data 
    filtered_array2 = np.copy(array2ds)
    filtered_array2[filtered_array2 < (array2_thresh)] = np.nan  # Masked values as NaN

    # Get coordinates for plotly
    x2, y2, z2 = np.meshgrid(np.arange(filtered_array2.shape[0]),
                        np.arange(filtered_array2.shape[1]),
                        np.arange(filtered_array2.shape[2]),
                        indexing='ij')
    x2_flat = x2.flatten()
    y2_flat = y2.flatten()
    z2_flat = z2.flatten()
    v2_flat = filtered_array2.flatten()


    # Generate figure
    fig = go.Figure()

    fig.add_trace(go.Volume(
        x=x1.flatten(),
        y=y1.flatten(),
        z=z1.flatten(),
        value=v1_flat.flatten(),
        isomin=array1_thresh,
        isomax=np.nanmax(v1_flat),
        opacity=0.9,
        surface_count=10,
        colorscale="blues",
        name="Moving Image data"
    ))

    fig.add_trace(go.Volume(
        x=x2.flatten(),
        y=y2.flatten(),
        z=z2.flatten(),
        value=v2_flat.flatten(),
        isomin=array2_thresh,
        isomax=np.nanmax(v2_flat),
        opacity=0.5,
        surface_count=10,
        colorscale="greens",
        name="Fixed Image atlas data"
    ))

    # Set layout options
    fig.update_layout(
        title="Bayesian alignment of Light Sheet Data on Allen Reference Atlas",
        scene=dict(
            xaxis=dict(title="X", range=[0, np.max(x1_flat)+5]),
            yaxis=dict(title="Y", range=[0, np.max(y1_flat)+5]),
            zaxis=dict(title="Z", range=[0, np.max(z1_flat)+5])
        )
    )

    now = datetime.now()
    timestamp = now.strftime("%Y_%m_%d_%H_%M_%S")
    output_filename = f"bayesian_mapping_{timestamp}.html"
    fig.write_html(os.path.join(r"C:\Users\listo\example_registration_data",output_filename))

def find_affine_matrix(fixed_image,moving_image,ntrials=10000,best_params=None):
    fixed_image_threshold = np.percentile(fixed_image,65)
    moving_image_threshold = np.percentile(moving_image,45)

    fixed_image = sitk.GetImageFromArray(fixed_image)
    moving_image = sitk.GetImageFromArray(moving_image)

    if best_params is None:

        # Define the objective function for Optuna optimization
        def objective(trial):
            # Sample rotation angles for x, y, and z axes
            theta_x = trial.suggest_float("theta_x", -np.pi / 2, np.pi / 2)  # -45° to +45°
            theta_y = trial.suggest_float("theta_y", -np.pi / 2, np.pi / 2)  # -45° to +45°
            theta_z = trial.suggest_float("theta_z", -np.pi / 2, np.pi / 2)  # -45° to +45°

            # Translation parameters
            translation_x = trial.suggest_float("translation_x", -10, 10)
            translation_y = trial.suggest_float("translation_y", -10, 10)
            translation_z = trial.suggest_float("translation_z", -10, 10)

            # Scaling factor
            scale = trial.suggest_float("scale", 1, 5)

            # Create an AffineTransform
            affine_transform = sitk.AffineTransform(3)
            affine_transform = set_affine_rotation(affine_transform, theta_x, theta_y, theta_z)
            affine_transform.SetTranslation([translation_x, translation_y, translation_z])
            affine_transform.Scale(scale)

            # Apply the affine transform to the moving image
            resampler = sitk.ResampleImageFilter()
            resampler.SetSize(fixed_image.GetSize())  # Resample to fixed image size
            resampler.SetOutputSpacing(fixed_image.GetSpacing())  # Resample to fixed image spacing
            resampler.SetTransform(affine_transform)  # Apply affine transform
            resampler.SetInterpolator(sitk.sitkLinear)  # Use linear interpolation
            transformed_image = resampler.Execute(moving_image)

            # Calculate the similarity metric (Mean Squared Error)
            mse = compute_mse(fixed_image, transformed_image)
            # Alternatively, you can use:
            # metric = sitk.MutualInformation(fixed_image, transformed_image)

            return mse  # Return the metric value (Optuna tries to minimize this)

        # Create an Optuna study to optimize the objective function
        study = optuna.create_study(direction="minimize")  # We want to minimize the metric
        study.optimize(objective, n_trials=ntrials, n_jobs=-1,  show_progress_bar=True)  # Run optimization for 100 trials

        # Get the best parameters from the optimization
        best_trial = study.best_trial
        print(f"Best trial: {best_trial.number}")
        print(f"Best value: {best_trial.value}")
        print(f"Best parameters: {best_trial.params}")

        # Apply the best affine transform to the moving image
        best_params = best_trial.params

    best_affine_transform = sitk.AffineTransform(3)
    best_affine_transform = set_affine_rotation(best_affine_transform, best_params['theta_x'], best_params['theta_y'], best_params['theta_z'])
    best_affine_transform.SetTranslation([best_params['translation_x'], best_params['translation_y'], best_params['translation_z']])
    best_affine_transform.Scale(best_params['scale'])

    # Resample the moving image with the best transform
    best_resampler = sitk.ResampleImageFilter()
    best_resampler.SetSize(fixed_image.GetSize())
    best_resampler.SetOutputSpacing(fixed_image.GetSpacing())
    best_resampler.SetTransform(best_affine_transform)
    best_resampler.SetInterpolator(sitk.sitkLinear)
    best_aligned_image = best_resampler.Execute(moving_image)

    aligned_array = sitk.GetArrayFromImage(best_aligned_image)
    fixed_image = sitk.GetArrayFromImage(fixed_image)
    
    plot_arrays_3d(array1=aligned_array,array2=fixed_image,array1_thresh=moving_image_threshold,array2_thresh=fixed_image_threshold)

    return fixed_image, aligned_array

