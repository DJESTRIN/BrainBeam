#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: bayessearch.py

Description: Using Bayesian Optimization (via optuna package), these functions find the optimal affine matrix to align two volumes. 
    For each moving image (ex. light sheet brain), a study (n=10000 trials) is created where we search for the optimal parameters to rigidly align the moving volume to the
    target volume. Ultimately, the best rotations, translations, scaling and dimensional scaling (x, y and/or z) will be output to align the moving image to target image. 
    The default criteria for aligning two images is Mattes Mutual Information (MMI). 

    Why was this written? For non-rigid registration (the following step after this code), it is critical that two volumes are aligned as precicely as possible. 
    If not, the alignment may never converge or look very distorted. When performing this step manually, I have found that retrieving the best affine matrix for rigid
    alignment is time consuming and is not garaunteed to work. Although this code may take hours to converge, it eliminates the need for user input and is more likely to 
    converge than manualy searching for the best affine matrix parameters. 

    What are the rigid alignment parameters that we are optimizing? (1) rotations: rotating around the x, y and z axis. (2) translations: moving the moving image along
    the x, y and z axis. (3) scaling: determining if the moving image needs to be increased or decreased in size to match the target image. (4) dimensional scaling: 
    determing whether specific axes (x, y and/or z) need to be squeezed or stretched compared to target image. 

Author: David Estrin
Date: 2025-01-07
Version: 2.0
"""
import optuna
from optuna.pruners import MedianPruner
import SimpleITK as sitk
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import ipdb
import plotly.graph_objects as go
from datetime import datetime
import os
from BrainBeam.cust_registration.graphics import volume_graphics, slice_views
from BrainBeam.cust_registration.padding import zoom_padding
from optuna.samplers import CmaEsSampler
from scipy.ndimage import zoom
from skimage.filters import threshold_otsu, threshold_li, threshold_yen


def print_results_every_n_trials(study, trial, n=10):
    """
    Callback function to print study results every n trials.
    """
    if trial.number % n == 0:
        print(f"Trial {trial.number}: Best Value = {study.best_value:.5f}, Best Params = {study.best_params}")


def compute_mattes_mutual_information(fixed_image, moving_image):
    registration_method = sitk.ImageRegistrationMethod()
    registration_method.SetMetricAsMattesMutualInformation(numberOfHistogramBins=50)
    identity_transform = sitk.Transform(3, sitk.sitkIdentity)
    registration_method.SetInitialTransform(identity_transform, inPlace=False)
    registration_method.SetOptimizerAsGradientDescent(learningRate=1.0, numberOfIterations=1)  # Zero iterations
    fixed_image = sitk.Cast(fixed_image, sitk.sitkFloat32) if fixed_image.GetPixelID() != sitk.sitkFloat32 else fixed_image
    moving_image = sitk.Cast(moving_image, sitk.sitkFloat32) if moving_image.GetPixelID() != sitk.sitkFloat32 else moving_image

    try:
        registration_method.Execute(fixed_image, moving_image)
        mutual_information = registration_method.GetMetricValue()
    except:
        mutual_information = -0.00000000000000000001 # default value suggesting failure

    return mutual_information

def set_affine_rotation(affine_transform, theta_x, theta_y, theta_z):
    """
    Set rotation for a SimpleITK AffineTransform using rotation angles (in radians) 
    for x, y, and z axes.
    """
    Rx = np.array([[1, 0, 0],
                   [0, np.cos(theta_x), -np.sin(theta_x)],
                   [0, np.sin(theta_x), np.cos(theta_x)]])
    
    Ry = np.array([[np.cos(theta_y), 0, np.sin(theta_y)],
                   [0, 1, 0],
                   [-np.sin(theta_y), 0, np.cos(theta_y)]])
    
    Rz = np.array([[np.cos(theta_z), -np.sin(theta_z), 0],
                   [np.sin(theta_z), np.cos(theta_z), 0],
                   [0, 0, 1]])
    R = Rz @ Ry @ Rx 
    affine_transform.SetMatrix(R.flatten().tolist())
    return affine_transform

def find_affine_matrix(fixed_image,moving_image, drop_dir,ntrials=10000,best_params=None):
    # Convert from numpy to sitk image
    slice_views(array=moving_image,output_filename='movingimagemask.jpg')
    slice_views(array=fixed_image,output_filename='fixedimagemask.jpg')
    fixed_image = sitk.GetImageFromArray(fixed_image)
    moving_image = sitk.GetImageFromArray(moving_image)

    if best_params is None:
        def objective(trial, fixed_image, moving_image):
            """ In this study, we are trying to determine which angles """
            theta_x = trial.suggest_float("theta_x", -np.pi/2, np.pi/2)  
            theta_y = trial.suggest_float("theta_y", -np.pi/2, np.pi/2) 
            theta_z = trial.suggest_float("theta_z", -np.pi/2, np.pi/2)  
            translation_x = trial.suggest_float("translation_x", -100, 100)
            translation_y = trial.suggest_float("translation_y", -100, 100)
            translation_z = trial.suggest_float("translation_z", -100, 100)
            scale = trial.suggest_float("scale", 0.7, 3)

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

            metric = compute_mattes_mutual_information(fixed_image, transformed_image)
            print(f'MMI value is {metric}')
            return metric  # Return the metric value (Optuna tries to minimize this)

        def current_param_graph(study, trial, moving_image, fixed_image, droppath, n=1000):
            if trial.number % n == 0:

                if trial.number ==0:
                    return 
                
                # Generate graphics object 
                bayesoptgraphs = volume_graphics(shots=45) 

                # Get the best trial
                best_trial = study.best_trial
                best_params = best_trial.params
                best_value = best_trial.value
                print(f"Plotting intermediate for the best trial, {best_trial.number}, which had the value of {best_trial.value}")

                # Get best affine
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

                # Convert sitk image to numpy arrays
                best_aligned_image = sitk.GetArrayFromImage(best_aligned_image)
                fixed_image = sitk.GetArrayFromImage(fixed_image)
                
                # Plot the results
                fig, axs = plt.subplots(3, 2, figsize=(30, 5))
                for i in range(3):
                    aligned_av = best_aligned_image.max(axis=i)
                    fixed_av = fixed_image.max(axis=i)

                    ax = axs[i, 0]
                    ax.imshow(aligned_av)
                    ax.axis('off') 

                    ax = axs[i, 1]
                    ax.imshow(fixed_av)
                    ax.axis('off')  

                plt.savefig(os.path.join(droppath,f'slices_trial_{trial.number}.jpg'))

        # Create an Optuna study to optimize the objective function
        sampler = CmaEsSampler()
        study = optuna.create_study(sampler=sampler, direction="minimize",pruner=MedianPruner())  # We want to minimize the metric
        study.optimize(lambda trial: objective(trial, fixed_image, moving_image), n_trials=ntrials, n_jobs=-1,  show_progress_bar=True, callbacks=[lambda s, t: current_param_graph(s, t, moving_image, fixed_image, drop_dir)])  # Run optimization for 100 trials

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
    return fixed_image, aligned_array, best_params

