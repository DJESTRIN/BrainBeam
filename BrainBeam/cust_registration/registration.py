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
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')
from PIL import Image
import glob
import tifffile as tiff
from scipy.ndimage import zoom
import tqdm
import SimpleITK as sitk
from BrainBeam.cust_registration.padding import zero_pad_arrays
from BrainBeam.cust_registration.bayessearch import find_affine_matrix, set_affine_rotation, find_best_axes_sampling
from BrainBeam.cust_registration.graphics import volume_graphics
from BrainBeam.cust_registration.preprocess import replace_signal
from datetime import datetime
from functools import partial
import argparse
import time
import pickle
from itertools import permutations

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
        def symmetry_score(line):
            """ Calculate symmetry to find the Right left axis """
            mirrored_line = line[::-1]  
            mse = np.mean((line - mirrored_line)**2)  
            return mse
        
        # Threshold data to remove background
        thresh_oh = np.percentile(self.template,60)
        threshed_sample = self.template.copy()
        threshed_sample[threshed_sample<thresh_oh] = 0

        # Calculate average intensity of data
        mean_intensity_x = np.nanmean(threshed_sample, axis=(1, 2)) 
        mean_intensity_y = np.nanmean(threshed_sample, axis=(0, 2)) 
        mean_intensity_z = np.nanmean(threshed_sample, axis=(0, 1))  

        # Gather meta data on average intensities
        av_szs = np.array([len(mean_intensity_x), len(mean_intensity_y), len(mean_intensity_z)])
        avs = np.array([mean_intensity_x, mean_intensity_y, mean_intensity_z])

        # Find the AP axis and determine whether it needs to be flipped
        longest_dim = np.where(av_szs == av_szs.max())
        
        AP = avs[longest_dim]
        if np.argmax(AP) < (len(AP) // 2):
            AP_flip=-1 # flip orientation
        else:
            AP_flip=1 # Keep orientation as not flipped

        # Determine the Right to Left axis
        # Note: We are not able to heuristically determine how to flip this dim
        scores = np.array([symmetry_score(line) for line in avs])
        mirror_dim = np.where(scores == scores.max())
        if mirror_dim[0] == longest_dim[0]:
            second_largest = np.partition(scores, -2)[-2]
            mirror_dim = np.where(scores == second_largest)

        # By process of elimination, determine Superior -> Inferior axis
        # Check whether any axes were chosen twice
        # Determine whether S->I needs to be flipped
        dims = {0, 1, 2}
        previous_dims = {int(longest_dim[0]), int(mirror_dim[0])}
        leftover_dim = list(dims - previous_dims)  # Subtract sets and extract the value

        if len(leftover_dim) == 1:
            leftover_dim=leftover_dim[0]
            SP = avs[leftover_dim]
        else:
            raise RuntimeError('Two dimensions were unable to be seperated')

        if np.argmax(SP) > (len(SP) // 2):
            SP_flip=-1 # flip orientation
        else:
            SP_flip=1 # Keep orientation as not flipped

        # Reioreint axes to R->L, S->I, A->P formattiong
        self.template_transposed = np.transpose(self.template, (int(mirror_dim[0]), int(leftover_dim), int(longest_dim[0]))) 

        if SP_flip == -1:
            self.template_transposed = self.template_transposed[:, ::-1, :]  # Flip the second axis (A)
        if AP_flip == -1:
            self.template_transposed = self.template_transposed[:, :, ::-1]  # Flip the third axis (R)

        self.template = self.template_transposed

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

    def normalize_template_stack(self):
        self.template = (self.template - self.template.min())/(self.template.max() - self.template.min())
        self.template = self.template * 255

    def __call__(self):
        self.download_atlas()
        self.download_template()
        self.determine_orientation()
        self.normalize_template_stack()
        if self.visualize:
            self.generate_gif(volume=self.template,full_filename=os.path.join(self.target_path,'template.gif'))
            self.generate_gif(volume=self.annotation,full_filename=os.path.join(self.target_path,'annotation.gif'))

class MovingImage:
    def __init__(self, image_path, drop_path, voxel_size=np.array([2,2.3,2.3]), ds_voxelsize=50, force_orientations=None, force_flips=None):
        self.image_path = image_path
        self.target_size = ds_voxelsize
        self.voxel_size = voxel_size
        self.drop_path = drop_path 
        self.force_orientations = force_orientations
        self.force_flips = force_flips

    def extract_number(self,file_path):
        # Extract digits using regex
        _,number = file_path.split('_0')
        number, _ = number.split('.')
        return int(number)

    def get_image_list(self):
        self.images = glob.glob(os.path.join(self.image_path,'*.tif*'))
        self.images = sorted(self.images, key=self.extract_number)

    def determine_orientation(self):
        if self.force_flips is not None or self.force_orientations is not None:
            """ Use force orientations for inputs """
            if self.force_orientations is not None:
                self.downsampled_volume_transposed = np.transpose(self.downsampled_volume, 
                                                                  (int(self.force_orientations[0]), 
                                                                   int(self.force_orientations[1]), 
                                                                   int(self.force_orientations[2]))) 

            if self.force_flips is not None:
                if self.force_flips[1] == -1:
                    self.downsampled_volume_transposed = self.downsampled_volume_transposed[:, ::-1, :]  # Flip the second axis (A)
                if self.force_flips[2] == -1:
                    self.downsampled_volume_transposed = self.downsampled_volume_transposed[:, :, ::-1]  # Flip the third axis (R)

        else:
            """ Automatically determine the orientation of brain """
            def symmetry_score(line):
                """ Calculate symmetry to find the Right left axis """
                mirrored_line = line[::-1]  
                mse = np.mean((line - mirrored_line)**2)  
                return mse
            
            # Threshold data to remove background
            thresh_oh = np.percentile(self.downsampled_volume,60)
            threshed_sample = self.downsampled_volume.copy()
            threshed_sample[threshed_sample<thresh_oh] = np.nan

            # Calculate average intensity of data
            mean_intensity_x = np.nanmean(threshed_sample, axis=(1, 2)) 
            mean_intensity_y = np.nanmean(threshed_sample, axis=(0, 2)) 
            mean_intensity_z = np.nanmean(threshed_sample, axis=(0, 1))  

            # Gather meta data on average intensities
            av_szs = np.array([len(mean_intensity_x), len(mean_intensity_y), len(mean_intensity_z)])
            avs = np.array([mean_intensity_x, mean_intensity_y, mean_intensity_z])

            # Find the AP axis and determine whether it needs to be flipped
            longest_dim = np.where(av_szs == av_szs.max())
            
            AP = avs[longest_dim]
            if np.argmax(AP) < (len(AP) // 2):
                AP_flip=1 # flip orientation
            else:
                AP_flip=-1 # Keep orientation as not flipped

            # Determine the Right to Left axis
            # Note: We are not able to heuristically determine how to flip this dim
            scores = np.array([symmetry_score(line) for line in avs])
            mirror_dim = np.where(scores == scores.max())
            if mirror_dim[0] == longest_dim[0]:
                second_largest = np.partition(scores, -2)[-2]
                mirror_dim = np.where(scores == second_largest)

            # By process of elimination, determine Superior -> Inferior axis
            # Check whether any axes were chosen twice
            # Determine whether S->I needs to be flipped
            dims = {0, 1, 2}
            previous_dims = {int(longest_dim[0]), int(mirror_dim[0])}
            leftover_dim = list(dims - previous_dims)  # Subtract sets and extract the value

            if len(leftover_dim) == 1:
                leftover_dim=leftover_dim[0]
                SP = avs[leftover_dim]
            else:
                raise RuntimeError('Two dimensions were unable to be seperated')

            if np.argmax(SP) > (len(SP) // 2):
                SP_flip=-1 # flip orientation
            else:
                SP_flip=1 # Keep orientation as not flipped

            # Reioreint axes to R->L, S->I, A->P formattiong
            self.downsampled_volume_transposed = np.transpose(self.downsampled_volume, (int(mirror_dim[0]), int(leftover_dim), int(longest_dim[0]))) 

            if SP_flip == -1:
                self.downsampled_volume_transposed = self.downsampled_volume_transposed[:, ::-1, :]  # Flip the second axis (A)
            if AP_flip == -1:
                self.downsampled_volume_transposed = self.downsampled_volume_transposed[:, :, ::-1]  # Flip the third axis (R)

        self.downsampled_volume = self.downsampled_volume_transposed

    def downsample(self,output_filename):
        if not os.path.isfile(output_filename):
            scaling_factors = [self.voxel_size[i] / self.target_size for i in range(3)]
            self.skip_factors = np.round(np.array([self.target_size, self.target_size, self.target_size]) / self.voxel_size).astype(np.uint8)
            downsampled_slices = []
            for i,slice_path in tqdm.tqdm(enumerate(self.images),total=len(self.images)):  # Replace with actual slice range
                if i% self.skip_factors[0]==0:
                    slice_img = tiff.imread(slice_path)  # Load 2D slice
                    downsampled_slice = slice_img[:: self.skip_factors[1],:: self.skip_factors[2]]
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
    
    def clip_high_signal(self,stack_oh,percentile=95):
        # Clip data based on percentile
        threshold = np.percentile(stack_oh,percentile)
        stack_oh = np.clip(stack_oh, a_min = 0, a_max = threshold)

        # Re-normalize to 0 -> 255 range
        stack_oh = (stack_oh - stack_oh.min())/(stack_oh.max() - stack_oh.min())
        stack_oh = stack_oh * 255
        return stack_oh

    def __call__(self):
        self.get_image_list()
        self.downsample(output_filename=os.path.join(self.drop_path,'downsampled_moving_image.tiff'))
        self.normalize_image_stack()
        self.downsampled_volume = self.adjust_brightness(stack_oh = self.downsampled_volume)
        self.determine_orientation()
        self.downsampled_volume = self.clip_high_signal(stack_oh = self.downsampled_volume)

class alignment:
    def __init__(self, MovingImageObject,TargetImageObject,drop_path,graphobjoh=None):
        self.MovingImageObject = MovingImageObject
        self.TargetImageObject = TargetImageObject
        self.drop_path = drop_path
        self.best_params_oh = None # Default assumption
        self.best_params_mask_oh = None
        self.best_params_mask_stretch_oh = None
        self.moving_array_original = self.MovingImageObject.downsampled_volume.astype(np.float64)
        self.target_array = self.TargetImageObject.template.astype(np.float64)
        self.annotation_array = self.TargetImageObject.annotation.astype(np.float64)
        self.graphobjoh = graphobjoh

    def multiresolution_align(self,  resolutions=None, iters=None):
        """ Multi-Resolution Alignment -- 
            Used for aligning two image volumes for light sheet imaging data.  """

        print('Setting up multiresolution alignment, generating global variables and call back command ... ')

        def command_iteration(method, n=5):
            iteration_oh = method.GetOptimizerIteration()
            metric_oh = method.GetMetricValue()
 
            # Print current iteration
            if iteration_oh % n == 0:
                print(f"Iteration: {iteration_oh}, Metric value: {metric_oh:.6f}")


        # Convert arrays to SimpleITK images
        fixed = sitk.GetImageFromArray(self.fixed_image) if isinstance(self.fixed_image, np.ndarray) else self.fixed_image
        moving = sitk.GetImageFromArray(self.moving_image) if isinstance(self.moving_image, np.ndarray) else self.moving_image

        # Convert to 32 float
        fixed = sitk.Cast(fixed, sitk.sitkFloat32)
        moving = sitk.Cast(moving, sitk.sitkFloat32)

        if resolutions is None:
            resolutions = [80.0, 40.0, 30.0] 
        
        if iters is None:
            iters = [100, 100, 50] 

        for resolution, nits in zip(resolutions,iters):
            transform_file = os.path.join(self.drop_path, f"transform_res{resolution}_iters{nits}.pkl")

            # Check if transform already exists
            if os.path.exists(transform_file):
                print(f"Transform for resolution {resolution} already exists. Loading transform...")
                with open(transform_file, "rb") as f:
                    current_transform = pickle.load(f)

            else:
                print(f"Resolution: {resolution}, Iterations {nits}")
                
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
                registration_method.SetMetricSamplingStrategy(registration_method.RANDOM)
                registration_method.SetOptimizerAsLBFGSB(numberOfIterations=nits)
                registration_method.SetOptimizerScalesFromPhysicalShift()
                registration_method.SetInitialTransform(init_transform, inPlace=False)
                registration_method.AddCommand(sitk.sitkIterationEvent, lambda: command_iteration(registration_method))

                # Execute registration and update the transform for the next resolution
                current_time = time.localtime()  # or time.gmtime() for UTC
                formatted_time = time.strftime("%I:%M %p", current_time)
                print(f"Starting registration at {formatted_time}...")
                current_transform = registration_method.Execute(fixed, moving)

                print("Saving transform into a file! ")
                with open(transform_file, "wb") as f:
                    pickle.dump(current_transform, f)
                    print(f"Transform saved to {transform_file}.")

            moving = sitk.Resample(moving, fixed, current_transform, sitk.sitkLinear, 0.0, moving.GetPixelID())
            moving_np = sitk.GetArrayFromImage(moving)

            self.graphobjoh.spin_volume(volume1 = moving_np, 
                                   volume2 = sitk.GetArrayFromImage(fixed), 
                                   label='multires',
                                   output=os.path.join(self.drop_path, f'MultiRes3d_{self.time_to_str()}.gif'))
            
        # Apply the final transformation to the moving image
        print('Applying final transformation to moving image ...')
        resampler = sitk.ResampleImageFilter()
        resampler.SetReferenceImage(sitk.GetImageFromArray(self.fixed_image))
        resampler.SetInterpolator(sitk.sitkLinear)
        resampler.SetTransform(current_transform)
        aligned_image = resampler.Execute(sitk.GetImageFromArray(self.moving_image))
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
        # Preprocess image volumes ... eliminate high signal
        self.moving_array_original = replace_signal(volume=self.moving_array_original) 
        self.target_array = replace_signal(volume = self.target_array, normalize=True)

        # Zero pad both arrays for consistent dimensions
        self.moving_array_original, self.target_array = zero_pad_arrays(array1=self.moving_array_original, array2=self.target_array)

        _, self.annotation_array_original = zero_pad_arrays(array1=self.moving_array_original, array2=self.annotation_array)
    
        # Binary mask alignment and stretching/squeezing
        self.moving_mask, self.target_mask = self.graphobjoh.plot_surface(volume1 = self.moving_array_original, 
                                     volume2 = self.target_array, pull_binary_mask = True) # Get binary masks 
        
        best_params_mask_file = os.path.join(self.drop_path, f"best_params_mask_bayesopt.pkl")
        best_params_mask_stretch_file = os.path.join(self.drop_path, f"best_params_mask_stretch_bayesopt.pkl")
        if os.path.exists(best_params_mask_file):
            """ If real, load in best rigid parameters """
            print(f"Bayes Opt file previously calculated for mask, loading file ...")
            with open(best_params_mask_file, "rb") as f:
                self.best_params_mask_oh = pickle.load(f)

        else:
            """ If no file exists, perform rigid transform via bayes search """
            print('Performing Bayesian-based rigid transformation ... ') 
            self.fixed_mask, self.moving_mask, self.best_params_mask_oh = find_affine_matrix(fixed_image=self.target_mask,
                                                                                             moving_image=self.moving_mask,
                                                                                             best_params=self.best_params_mask_oh, 
                                                                                             drop_dir = self.drop_path,
                                                                                             ntrials=5000)
            
            self.fixed_mask,self.moving_mask,self.best_params_mask_stretch_oh = find_best_axes_sampling(fixed_image=self.fixed_mask,
                                                                                                        moving_image=self.moving_mask,
                                                                                                        best_params=self.best_params_mask_stretch_oh, 
                                                                                                        drop_dir = self.drop_path, 
                                                                                                        ntrials=5000)

            with open(best_params_mask_file, "wb") as f:
                pickle.dump(self.best_params_mask_oh, f)
                print('Saved BayesOpt best parameters rigid mask ...')

            with open(best_params_mask_stretch_file, "wb") as f:
                pickle.dump(self.best_params_mask_stretch_oh, f)
                print('Saved BayesOpt best parameters stretch mask ...')

        # Apply alignment to data 
        assert self.best_params_mask_oh is not None
        assert self.best_params_mask_stretch_oh is not None
        
        best_affine_transform = sitk.AffineTransform(3)
        best_affine_transform = set_affine_rotation(best_affine_transform, self.best_params_mask_oh['theta_x'], self.best_params_mask_oh['theta_y'], self.best_params_mask_oh['theta_z'])
        best_affine_transform.SetTranslation([self.best_params_mask_oh['translation_x'], self.best_params_mask_oh['translation_y'], self.best_params_mask_oh['translation_z']])
        best_affine_transform.Scale(self.best_params_mask_oh['scale'])
        best_resampler = sitk.ResampleImageFilter()
        best_resampler.SetSize(sitk.GetImageFromArray(self.target_array).GetSize())
        best_resampler.SetOutputSpacing(sitk.GetImageFromArray(self.target_array).GetSpacing())
        best_resampler.SetTransform(best_affine_transform)
        best_resampler.SetInterpolator(sitk.sitkLinear)
        best_aligned_image = best_resampler.Execute(sitk.GetImageFromArray(self.moving_array_original))
        self.moving_image = sitk.GetArrayFromImage(best_aligned_image)
        self.fixed_image = self.target_array
        self.moving_image = zoom(self.moving_image, (self.best_params_mask_stretch_oh['scale_x'], self.best_params_mask_stretch_oh['scale_y'], self.best_params_mask_stretch_oh['scale_z'])) 

        # Perform Rigid Alignment on original data 
        best_params_file = os.path.join(self.drop_path, f"best_params_bayesopt.pkl")
        if os.path.exists(best_params_file):
            """ If real, load in best rigid parameters """
            print(f"Bayes Opt file previously calculated, loading file ...")
            with open(best_params_file, "rb") as f:
                self.best_params_oh = pickle.load(f)

            # Perform rigid transform on moving image
            best_affine_transform = sitk.AffineTransform(3)
            best_affine_transform = set_affine_rotation(best_affine_transform, self.best_params_oh['theta_x'], self.best_params_oh['theta_y'], self.best_params_oh['theta_z'])
            best_affine_transform.SetTranslation([self.best_params_oh['translation_x'], self.best_params_oh['translation_y'], self.best_params_oh['translation_z']])
            best_affine_transform.Scale(self.best_params_oh['scale'])
            best_resampler = sitk.ResampleImageFilter()
            best_resampler.SetSize(sitk.GetImageFromArray(self.target_array).GetSize())
            best_resampler.SetOutputSpacing(sitk.GetImageFromArray(self.target_array).GetSpacing())
            best_resampler.SetTransform(best_affine_transform)
            best_resampler.SetInterpolator(sitk.sitkLinear)
            best_aligned_image = best_resampler.Execute(sitk.GetImageFromArray(self.moving_array_original))
            self.moving_image = sitk.GetArrayFromImage(best_aligned_image)
            self.fixed_image = self.target_array

        else:
            """ If no file exists, perform rigid transform via bayes search """
            print('Performing Bayesian-based rigid transformation ... ') 
            self.fixed_image, self.moving_image, self.best_params_oh = find_affine_matrix(fixed_image=self.fixed_image,
                                                                    moving_image=self.moving_image,
                                                                    best_params=self.best_params_oh, 
                                                                    drop_dir = self.drop_path)
            
            with open(best_params_file, "wb") as f:
                pickle.dump(self.best_params_oh, f)
                print('Saved BayesOpt best parameters ...')

        # Perform non-rigid alignment
        print('Performing Non-Rigid Multiresolution Alignment ... ') 
        self.nonrigid_moving_image = self.multiresolution_align()

def cli_parser():
    """ Takes command line inputs and parses them for downstream """
    parser = argparse.ArgumentParser()
    parser.add_argument('--image_path',type=str,help='Full path to best qualtiy light sheet images for registration ...')
    parser.add_argument('--atlas_path',type=str,help="Full path to folder containing atlas. If folder is empty, atlas is downloaded")
    parser.add_argument('--output_path',type=str,help='Full path containin results. Path will be appended with subfolder containing current date and time. \
                        These subfolders are where data will be saved.')
    parser.add_argument('--force_orientation',type=int,nargs='+', default=None, required=False, help='3 Integers which force orientation of moving image')
    parser.add_argument('--force_flips',type=int,nargs='+', default=None, required=False, help='3 Integers which force orientation of moving image')
    args = parser.parse_args()

    # Get current time as string and generate output folder
    now = datetime.now()
    init_date_time= now.strftime("%Y_%m_%d_%H_%M_%S")
    new_folder = f'current_run_{init_date_time}'
    output_path = os.path.join(args.output_path,new_folder)
    if not os.path.exists(output_path): 
        os.makedirs(output_path)

    # Append a few new arguments
    args.output_path = output_path
    args.init_date_time = init_date_time
    return args

def main(args):
    # Parse command line inputs

    # Update classes to have matching methods
    MovingImage.generate_gif = target.generate_gif 
    alignment.generate_gif = target.generate_gif 

    # Generate target and MovingImage objects
    target_oh = target(target_path=args.atlas_path)
    target_oh()

    Image_oh = MovingImage(image_path = args.image_path, drop_path=args.output_path, force_orientations=args.force_orientation, force_flips=args.force_flips)
    Image_oh()

    Image_oh.generate_gif(volume=Image_oh.downsampled_volume,full_filename=os.path.join(args.output_path,f'init_moving_array_{args.init_date_time}.gif'))
    Image_oh.generate_gif(volume=target_oh.template,full_filename=os.path.join(args.output_path,f'init_target_array_{args.init_date_time}.gif'))    

    # Perform alignment
    graphobj = volume_graphics()
    alignment_object = alignment(MovingImageObject=Image_oh, TargetImageObject=target_oh, graphobjoh = graphobj, drop_path=args.output_path)
    alignment_object() 

    # Save most important arrays
    np.save(os.path.join(args.output_path,'downsampled_volume.npy'), Image_oh.downsampled_volume) # The original downsampled array without padding
    np.save(os.path.join(args.output_path,'template_volume.npy'), target_oh.template) # The orignal atlas without padding as np array
    np.save(os.path.join(args.output_path,'moving_array_original.npy'), alignment_object.moving_array_original) # The original array with zero padding
    np.save(os.path.join(args.output_path,'nonrigid_moving_image.npy'), alignment_object.nonrigid_moving_image) # The final array after alignment
    np.save(os.path.join(args.output_path,'target_array.npy'), alignment_object.target_array) # The target array with zero padding

    # Append saved numpy file paths to args
    args.downsampled_volume_path = os.path.join(args.output_path,'downsampled_volume.npy')
    args.template_volume_path = os.path.join(args.output_path,'template_volume.npy')
    args.moving_array_original_path = os.path.join(args.output_path,'moving_array_original.npy')
    args.nonrigid_moving_image_path = os.path.join(args.output_path,'nonrigid_moving_image.npy')
    args.target_array_path = os.path.join(args.output_path,'target_array.npy')
    return args
   
if __name__=='__main__':
    args = cli_parser()
    main(args)

   
    # Example cli usage

    # python ./registration.py --image_path c:\Users\listo\example_registration_data\sub3 --atlas_path c:\Users\listo\example_registration_data\atlas --output_path c:\Users\listo\example_registration_data\sub3_output --force_orientation 1 0 2 --force_flips 1 -1 1 
    
    