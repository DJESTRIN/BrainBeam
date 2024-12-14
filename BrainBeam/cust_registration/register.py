#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: register.py
Description: This code is meant to assist with aligning light sheet data volumes via sitk. 
Author: David Estrin
Date: 2024-12-11
Version: 1.0
"""
# Import dependencies
import numpy as np
import os
from allensdk.core.reference_space_cache import ReferenceSpaceCache
from pathlib import Path
import ipdb
import matplotlib.pyplot as plt
from PIL import Image
import glob
import tifffile as tiff
from scipy.ndimage import zoom
import tqdm
import SimpleITK as sitk
from BrainBeam.cust_registration.padding import zero_pad_arrays
from BrainBeam.cust_registration.BayesSearch import find_affine_matrix
from datetime import datetime
from functools import partial
import argparse
import time
import pickle

# Set max hyper threading
max_threads = os.cpu_count()
sitk.ProcessObject.SetGlobalDefaultNumberOfThreads(max_threads)

# Custom classes and functions
class target:
    def __init__(self, target_path, voxelsize=50, visualize=True):
        self.target_path = target_path
        if not os.path.exists(self.target_path):
            os.mkdir(self.target_path)

        self.voxelsize = voxelsize
        self.visualize = visualize

    def download_atlas(self):
        reference_space_key = os.path.join('annotation/', 'ccf_2017')
        rspc = ReferenceSpaceCache(self.voxelsize, reference_space_key, manifest=Path(self.target_path) / 'manifest_atlas.json')
        self.annotation_tree = rspc.get_structure_tree(structure_graph_id=1) 
        self.annotation, self.annotation_meta = rspc.get_annotation_volume()

    def download_template(self):
        reference_space_key = 'average_template/'
        rspc = ReferenceSpaceCache(self.voxelsize, reference_space_key, manifest=Path(self.target_path) / 'manifest.json')
        self.template_tree = rspc.get_structure_tree(structure_graph_id=1) 
        self.template, self.template_meta = rspc.get_template_volume()
    
    def determine_orientation(self):
        mean_intensity_x = np.mean(self.template, axis=(1, 2))  # mean along x-axis (rows)
        mean_intensity_y = np.mean(self.template, axis=(0, 2))  # mean along y-axis (columns)
        mean_intensity_z = np.mean(self.template, axis=(0, 1))  # mean along z-axis (slices)

    def generate_gif(self, volume, full_filename, volume2=None):
        if not os.path.isfile(full_filename):
            if volume2 is None:
                frames = []
                for i in range(volume.shape[0]):
                    fig, ax = plt.subplots()
                    ax.imshow(volume[i, :, :], cmap="gray", vmin=volume.min(), vmax=volume.max())
                    ax.axis("off")
                    fig.canvas.draw()
                    image = Image.frombytes('RGB', fig.canvas.get_width_height(),fig.canvas.tostring_rgb())
                    frames.append(image)
                    plt.close(fig)
                frames[0].save(full_filename, save_all=True, append_images=frames[1:], duration=50, loop=0)
            else:
                frames = []
                for i in range(volume.shape[0]):
                    fig, ax = plt.subplots()
                    ax.imshow(volume[i, :, :], cmap="Blues", vmin=volume.min(), vmax=volume.max(),alpha=0.99)
                    ax.imshow(volume2[i, :, :], cmap="Oranges", vmin=volume.min(), vmax=volume.max(), alpha=0.05)
                    ax.axis("off")
                    fig.canvas.draw()
                    image = Image.frombytes('RGB', fig.canvas.get_width_height(),fig.canvas.tostring_rgb())
                    frames.append(image)
                    plt.close(fig)
                frames[0].save(full_filename, save_all=True, append_images=frames[1:], duration=50, loop=0)

    def __call__(self):
        self.download_atlas()
        self.download_template()
        self.determine_orientation()
        if self.visualize:
            self.generate_gif(volume=self.template,full_filename=os.path.join(self.target_path,'template.gif'))
            self.generate_gif(volume=self.annotation,full_filename=os.path.join(self.target_path,'annotation.gif'))


class MovingImage:
    def __init__(self, image_path, voxel_size=np.array([2,2.3,2.3]), ds_voxelsize=50, visualize=True):
        self.image_path = image_path
        self.target_size = ds_voxelsize
        self.voxel_size = voxel_size

    def extract_number(self,file_path):
        # Extract digits using regex
        _,number = file_path.split('_0')
        number, _ = number.split('.')
        return int(number)

    def get_image_list(self):
        self.images = glob.glob(os.path.join(self.image_path,'*.tif*'))
        self.images = sorted(self.images, key=self.extract_number)

    def determine_orientation(self):
        mean_intensity_x = np.mean(self.downsampled_volume, axis=(1, 2))  # mean along x-axis (rows)
        mean_intensity_y = np.mean(self.downsampled_volume, axis=(0, 2))  # mean along y-axis (columns)
        mean_intensity_z = np.mean(self.downsampled_volume, axis=(0, 1))  # mean along z-axis (slices)

        # Use AUC to determine which side has olfactory bulb
        halfway = len(mean_intensity_x) // 2
        if np.trapz(mean_intensity_x[:halfway])<np.trapz(mean_intensity_x[halfway:]):
            print('front on left')
        else:
            print('front on right')

    def downsample(self,output_filename):
        if not os.path.isfile(output_filename):
            scaling_factors = [self.voxel_size[i] / self.target_size for i in range(3)]
            skip_factors = np.round(np.array([self.target_size, self.target_size, self.target_size]) / self.voxel_size).astype(np.uint8)
            downsampled_slices = []
            for i,slice_path in tqdm.tqdm(enumerate(self.images),total=len(self.images)):  # Replace with actual slice range
                if i%skip_factors[0]==0:
                    slice_img = tiff.imread(slice_path)  # Load 2D slice
                    downsampled_slice = slice_img[::skip_factors[1],::skip_factors[2]]
                    downsampled_slices.append(downsampled_slice)

            self.downsampled_volume = np.stack(downsampled_slices, axis=0)
            tiff.imwrite(output_filename, self.downsampled_volume.astype(np.uint16))

        else:
            self.downsampled_volume = tiff.imread(output_filename)
    
    def normalize_image_stack(self):
        self.downsampled_volume = (self.downsampled_volume - self.downsampled_volume.min())/(self.downsampled_volume.max() - self.downsampled_volume.min())
        self.downsampled_volume = self.downsampled_volume * 255

    def adjust_brightness(self, stack_oh, factor=10):
        """Increase brightness by scaling pixel values."""
        stack_oh = stack_oh * factor
        stack_oh = np.clip(stack_oh, 0, 255)  # Ensure values are within the 0-255 range
        return stack_oh

    def __call__(self):
        self.get_image_list()
        self.downsample(output_filename=r'C:\Users\listo\example_registration_data\test.tiff')
        self.normalize_image_stack()
        self.downsampled_volume = self.adjust_brightness(stack_oh = self.downsampled_volume)
        self.downsampled_volume = np.transpose(self.downsampled_volume, (1, 0, 2))
        self.downsampled_volume = self.downsampled_volume[::-1, :, :] 
        self.determine_orientation()

class alignment:
    def __init__(self, MovingImageObject,TargetImageObject,drop_path):
        self.MovingImageObject = MovingImageObject
        self.TargetImageObject = TargetImageObject
        self.drop_path = drop_path
        self.best_params_oh = None # Default assumption
        self.moving_array_original = self.MovingImageObject.downsampled_volume.astype(np.float64)
        self.target_array = self.TargetImageObject.template.astype(np.float64)
        self.annotation_array = self.TargetImageObject.annotation.astype(np.float64)

    def multiresolution_align(self,  resolutions=None):
        """ Multi-Resolution Alignment -- 
            Used for aligning two image volumes for light sheet imaging data.  """

        print('Setting up multiresolution alignment, generating global variables and call back command ... ')
        global best_metric, plateau_counter
        best_metric = 0 
        plateau_counter = 0  

        def command_iteration(method, n=20, patience=15):
            global best_metric, plateau_counter
            iteration_oh = method.GetOptimizerIteration()
            metric_oh = method.GetMetricValue()
            abs_metric = np.abs(metric_oh)

            # Print current iteration
            if iteration_oh % n == 0:
                print(f"Iteration: {iteration_oh}, Metric value: {metric_oh:.6f}")

            # Determine if data has plateaud 
            if abs_metric > best_metric :
                best_metric = abs_metric 
                plateau_counter = 0
            else:
                plateau_counter += 1 
            
            # Stop optimization if plateau detected
            if plateau_counter >= patience:
                raise RuntimeError('Plateu detected so stopping optimization. Please wait for next resolution if there is one.') 

        # Convert arrays to SimpleITK images
        fixed = sitk.GetImageFromArray(self.fixed_image) if isinstance(self.fixed_image, np.ndarray) else self.fixed_image
        moving = sitk.GetImageFromArray(self.moving_image) if isinstance(self.moving_image, np.ndarray) else self.moving_image

        # Convert to 32 float
        fixed = sitk.Cast(fixed, sitk.sitkFloat32)
        moving = sitk.Cast(moving, sitk.sitkFloat32)

        if resolutions is None:
            resolutions = [80.0, 40.0, 30.0, 20.0, 15.0] 

        for resolution in resolutions:
            transform_file = os.path.join(self.drop_path, f"transform.pkl")

            # Check if transform already exists
            if os.path.exists(transform_file):
                print(f"Transform for resolution {resolution} already exists. Loading transform...")
                with open(transform_file, "rb") as f:
                    current_transform = pickle.load(f)

            else:
                print(f"Resolution: {resolution}")
                
                # Set grid physical spacing and compute mesh size
                grid_physical_spacing = [resolution] * 3
                image_physical_size = [size * spacing for size, spacing in zip(fixed.GetSize(), fixed.GetSpacing())]
                grid_size = [int(image_physical_size[i] / grid_physical_spacing[i] + 0.5) for i in range(3)]
                
                # Compute B-spline mesh size
                transform_domain_mesh_size = [max(1, grid_size[i] - 3) for i in range(3)]
                print(f"Mesh size: {transform_domain_mesh_size}")

                # Update the transform mesh size (keeping current_transform values)
                init_transform = sitk.BSplineTransformInitializer(fixed, transformDomainMeshSize=transform_domain_mesh_size, order=3)
        
                # Set up the registration method
                registration_method = sitk.ImageRegistrationMethod()
                registration_method.SetMetricAsMattesMutualInformation(numberOfHistogramBins=50)
                registration_method.SetOptimizerAsLBFGSB(numberOfIterations=10000)
                registration_method.SetInitialTransform(init_transform, inPlace=False)
                registration_method.AddCommand(sitk.sitkIterationEvent, lambda: command_iteration(registration_method))

                # Execute registration and update the transform for the next resolution
                current_time = time.localtime()  # or time.gmtime() for UTC
                formatted_time = time.strftime("%I:%M %p", current_time)
                print(f"Starting registration at {formatted_time}...")
                try:
                    current_transform = registration_method.Execute(fixed, moving)
                except Exception as e:
                    print(f"Registration ended: {e}")

                print("Saving transform into a file! ")
                with open(transform_file, "wb") as f:
                    pickle.dump(current_transform, f)
                    print(f"Transform saved to {transform_file}.")

            moving = sitk.Resample(moving, fixed, current_transform, sitk.sitkLinear, 0.0, moving.GetPixelID())
            moving_np = sitk.GetArrayFromImage(moving)

            self.generate_gif(volume2=sitk.GetArrayFromImage(fixed), volume=moving_np, 
                        full_filename=os.path.join(self.drop_path, f'multir_Non_Rigid_vs_fixed_{self.time_to_str()}.gif'))

        # Apply the final transformation to the moving image
        print('Applying final transformation to moving image ...')
        resampler = sitk.ResampleImageFilter()
        resampler.SetReferenceImage(self.fixed_image)
        resampler.SetInterpolator(sitk.sitkLinear)
        resampler.SetTransform(current_transform)
        aligned_image = resampler.Execute(self.moving_image)
        aligned_array = sitk.GetArrayFromImage(aligned_image)
        self.final_transform = current_transform
        return aligned_array

    def inverse_multiresolution_align(self):
        """ Takes results from multiresolution alignment and generates the inverse alignment.
        This allows one to map the fixed image onto the moving image. For example, this is usual for aligning the 
        atlas back onto the raw data. 
        """
        # Convert from numpy back to 
        fixed = sitk.GetImageFromArray(self.fixed_image) if isinstance(self.fixed_image, np.ndarray) else self.fixed_image
        moving = sitk.GetImageFromArray(self.moving_image) if isinstance(self.moving_image, np.ndarray) else self.moving_image
        annotation = sitk.GetImageFromArray(self.annotation_array_original) if isinstance(self.annotation_array_original, np.ndarray) else self.annotation_array_original

        # Get the inverse of final transform for target image
        inverse_transform = self.final_transform.GetInverse()

        # Perform inverse transform on atlas/fixed image to moving orginal data image
        fixed_to_moving = sitk.Resample(fixed, moving, inverse_transform, sitk.sitkLinear, 0.0, fixed.GetPixelID())
        annotation_to_moving = sitk.Resample(annotation, moving, inverse_transform, sitk.sitkLinear, 0.0, fixed.GetPixelID())
        return sitk.GetArrayFromImage(fixed_to_moving), sitk.GetArrayFromImage(annotation_to_moving)
    
    def time_to_str(self):
        now = datetime.now()
        return now.strftime("%Y_%m_%d_%H_%M_%S")

    def __call__(self):
        # Zero pad both arrays for consistent dimensions
        self.moving_array_original, self.target_array = zero_pad_arrays(array1=self.moving_array_original, 
                                                                        array2=self.target_array)

        _, self.annotation_array_original = zero_pad_arrays(array1=self.moving_array_original, 
                                                                        array2=self.annotation_array)

        # Perform a rigid transformation
        print('Performing Bayesian-based rigid transformation ... ') 
        self.fixed_image, self.moving_image = find_affine_matrix(fixed_image=self.target_array,
                                                                moving_image=self.moving_array_original,
                                                                best_params=self.best_params_oh)
        self.generate_gif(volume=self.moving_image, 
                        volume2=self.fixed_image, 
                        full_filename=os.path.join(self.drop_path, f'Rigid_Bayes_Alignment_{self.time_to_str()}.gif'))

        # Perform non-rigid alignment
        print('Performing Non-Rigid Multiresolution Alignment ... ') 
        self.nonrigid_moving_image = self.multiresolution_align()

        # Generate final visualizations
        self.generate_gif(volume=self.nonrigid_moving_image, 
                        volume2=self.fixed_image, 
                        full_filename=os.path.join(self.drop_path, f'FINAL_Non_Rigid_Alignment_{self.time_to_str()}.gif'))

        # Map fixed image to moving image
        self.fixed2moving, self.annotation2moving = self.inverse_multiresolution_align()

        self.generate_gif(volume=self.moving_array_original, 
                        volume2=self.fixed2moving, 
                        full_filename=os.path.join(self.drop_path, f'Fixed_On_Moving_{self.time_to_str()}.gif'))
        
        self.generate_gif(volume=self.moving_array_original, 
                        volume2=self.annotation2moving, 
                        full_filename=os.path.join(self.drop_path, f'Annotation_On_Moving_{self.time_to_str()}.gif'))

def cli_parser():
    """ Takes command line inputs and parses them for downstream """
    # Note: Replace later with real
    data_path=r'C:\Users\listo\example_registration_data\Ex_561_Em_600'
    atlas_path=r'C:\Users\listo\example_registration_data\atlas'
    results_drop_path=r'C:\Users\listo\example_registration_data\full_run2'
    
    now = datetime.now()
    init_date_time= now.strftime("%Y_%m_%d_%H_%M_%S")
    return data_path, atlas_path, results_drop_path, init_date_time

if __name__=='__main__':
    # Parse command line inputs
    data_path, atlas_path, results_drop_path, init_date_time = cli_parser()

    # Update classes to have matching methods
    MovingImage.generate_gif = target.generate_gif 
    alignment.generate_gif = target.generate_gif 

    # Generate target and MovingImage objects
    target_oh = target(target_path=atlas_path)
    target_oh()

    Image_oh = MovingImage(image_path = data_path)
    Image_oh()
    Image_oh.generate_gif(volume=Image_oh.downsampled_volume,full_filename=os.path.join(results_drop_path,'init_moving_array_{init_date_time}.gif'))

    # Perform alignment
    alignment_object = alignment(MovingImageObject=Image_oh,TargetImageObject=target_oh, drop_path=results_drop_path)
    alignment_object.best_params_oh = {'theta_x': -0.06592113854402398, 
                                       'theta_y': -0.05142325682030642, 
                                       'theta_z': -0.09306829138697534, 
                                       'translation_x': 0.11337105960975358, 
                                       'translation_y': -4.433834555094086, 
                                       'translation_z': -7.1064966638613605, 
                                       'scale': 1.0502485559828962}
    alignment_object() 
