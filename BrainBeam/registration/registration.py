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
from scipy.ndimage import distance_transform_edt
import ipdb
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')
from PIL import Image
import glob
import tifffile as tiff
from scipy.ndimage import zoom, binary_dilation, binary_fill_holes, binary_erosion
import tqdm
import SimpleITK as sitk
from BrainBeam.registration.padding import zero_pad_arrays
from BrainBeam.registration.bayessearch import find_affine_matrix, set_affine_rotation, manual_find_axes_sampling, adjust_volume_shape, MMI
from BrainBeam.registration.graphics import volume_graphics, slice_views
from BrainBeam.registration.preprocess import replace_signal
from BrainBeam.registration.cellalignment import cellalignment
from datetime import datetime
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
    def __init__(self, image_path, drop_path, voxel_size=np.array([2,2.3,2.3]), ds_voxelsize=50, 
                 force_orientations=None, force_flips=None, crop_border_noise_bool=False):
        self.image_path = image_path
        self.target_size = ds_voxelsize
        self.voxel_size = voxel_size
        self.drop_path = drop_path 
        self.force_orientations = force_orientations
        self.force_flips = force_flips
        self.crop_border_noise_bool = crop_border_noise_bool

    def extract_number(self,file_path):
        # Extract digits using regex
        number = file_path.split('_')[-1]
        number, _ = number.split('.')
        return int(number)

    def get_image_list(self):
        self.images = glob.glob(os.path.join(self.image_path,'*.tif*'))
        self.images = sorted(self.images, key=self.extract_number)

    def grab_original_image_medidata(self):
        self.orig_z_dim = len(self.images)
        img_oh = tiff.imread(self.images[0])
        self.orig_x_dim, self.orig_y_dim = img_oh.shape

    def determine_orientation(self):
        if self.force_flips is not None or self.force_orientations is not None:
            """ Use force orientations for inputs """
            if self.force_orientations is not None:
                self.downsampled_volume_transposed = np.transpose(self.downsampled_volume, 
                                                                  (int(self.force_orientations[0]), 
                                                                   int(self.force_orientations[1]), 
                                                                   int(self.force_orientations[2]))) 

            print(f'This is what force flips is set to inside moving image: {self.force_flips}')
            if self.force_flips is not None:
                if self.force_flips[0]==-1:
                    self.downsampled_volume_transposed = np.copy(self.downsampled_volume_transposed[::-1, :, :]) # Flip the first axis (Dosral-Ventral)
                if self.force_flips[1] == -1:
                    self.downsampled_volume_transposed = np.copy(self.downsampled_volume_transposed[:, ::-1, :]) # Flip the second axis (Right-Left)
                if self.force_flips[2] == -1:
                    self.downsampled_volume_transposed = np.copy(self.downsampled_volume_transposed[:, :, ::-1])  # Flip the third axis (Anterior-Posterior)

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
            print('If force flips or force orientation is on, this should not be printing right now...')

        return self.downsampled_volume_transposed

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
    
    def crop_border_noise(self, stack_oh, distance_threshold=10,artificial_padding=5):
        """ Try to eliminate noise at the border of tissue """
        print('We are cropping noise on border!')
        padded_stack_oh = np.pad(stack_oh, artificial_padding, mode='constant', constant_values=-1)
        distances_oh = distance_transform_edt(padded_stack_oh != -1)
        cleaned_padded_stack_oh = np.where(distances_oh > distance_threshold, padded_stack_oh, 0)
        cropped_volume = cleaned_padded_stack_oh[artificial_padding:-artificial_padding, 
                                        artificial_padding:-artificial_padding, 
                                        artificial_padding:-artificial_padding]
        slice_views(array1=cropped_volume,output_filename=os.path.join(self.drop_path,"cropped_borderoutput.jpg"))
        return cropped_volume

    def __call__(self):
        self.get_image_list()
        self.grab_original_image_medidata()
        self.downsample(output_filename=os.path.join(self.drop_path,'downsampled_moving_image.tiff'))
        self.normalize_image_stack()
        self.downsampled_volume = self.adjust_brightness(stack_oh = self.downsampled_volume)
        self.downsampled_volume = self.determine_orientation()
        self.downsampled_volume = self.crop_border_noise(stack_oh = self.downsampled_volume, distance_threshold=10, artificial_padding=5)
        self.downsampled_volume = self.clip_high_signal(stack_oh = self.downsampled_volume)

class alignment:
    def __init__(self, MovingImageObject,TargetImageObject,drop_path,graphobjoh=None, align_binary_mask=False):
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
        if align_binary_mask is None:
            align_binary_mask = False
        self.align_binary_mask = align_binary_mask
        

    def multiresolution_align(self,  resolutions=None, iters=None):
        """ Multi-Resolution Alignment -- 
            Used for aligning two image volumes for light sheet imaging data.  """

        print('Setting up multiresolution alignment, generating global variables and call back command ... ')

        def command_iteration(method, n=5):
            """ Prints current value to command line """
            iteration_oh = method.GetOptimizerIteration()
            metric_oh = method.GetMetricValue()
 
            # Print current iteration
            if iteration_oh % n == 0:
                print(f"Iteration: {iteration_oh}, Metric value: {metric_oh:.6f}")

        def alignoh(resolution, nits, fixed, moving, iteration_number, attempt=0, current_transform=None, transform_file="transform.pkl"):
            """Runs alignment and collects MMI data for each trial."""
            print(f"Resolution: {resolution}, Iterations: {nits}")
            
            # Update transform file
            name, fileend = transform_file.split('.')
            transform_file = os.path.join(self.drop_path, f"nonrigid_{name}_resolution{int(resolution)}_attempt{attempt}_step{iteration_number}.{fileend}")

            # Set grid physical spacing and compute mesh size
            grid_physical_spacing = [resolution] * 3
            image_physical_size = [size * spacing for size, spacing in zip(fixed.GetSize(), fixed.GetSpacing())]
            grid_size = [int(image_physical_size[i] / grid_physical_spacing[i] + 0.5) for i in range(3)]
            
            # Compute B-spline mesh size
            transform_domain_mesh_size = [max(1, grid_size[i] - 3) for i in range(3)]
            print(f"Mesh size: {transform_domain_mesh_size}")

            # Initialize list to store MMI data
            mmi_results = []

            # Initialize or update the transform
            if current_transform is None:
                init_transform = sitk.BSplineTransformInitializer(fixed, transformDomainMeshSize=transform_domain_mesh_size, order=3)

            else:
                init_transform = current_transform

            # Set up the registration method
            registration_method = sitk.ImageRegistrationMethod()
            registration_method.SetMetricAsMattesMutualInformation(numberOfHistogramBins=100)
            registration_method.SetMetricSamplingStrategy(registration_method.RANDOM)
            registration_method.SetMetricSamplingPercentage(1.0)
            # registration_method.SetOptimizerAsRegularStepGradientDescent(learningRate=1.0, minStep=1e-6, 
            #                                                              numberOfIterations=nits, gradientMagnitudeTolerance=1e-6)
            registration_method.SetOptimizerAsLBFGSB(numberOfIterations=nits, gradientConvergenceTolerance=1e-9)
            registration_method.SetOptimizerScalesFromPhysicalShift()
            registration_method.SetInitialTransform(init_transform, inPlace=False)
            registration_method.AddCommand(sitk.sitkIterationEvent, lambda: command_iteration(registration_method))

            # Execute registration and capture the MMI value
            current_time = time.localtime()  # or time.gmtime() for UTC
            formatted_time = time.strftime("%I:%M %p", current_time)
            print(f"Starting registration at {formatted_time}...")
            current_transform = registration_method.Execute(fixed, moving)

            # Store the final MMI value for this trial
            final_mmi_value = registration_method.GetMetricValue()
            mmi_results.append(final_mmi_value)

            # Save the final transform into a file
            print("Saving transform into a file!")
            with open(transform_file, "wb") as f:
                pickle.dump(current_transform, f)
                print(f"Transform saved to {transform_file}.")

            return mmi_results, current_transform

        def plateau_cumsum(criteria_data, window_size=10,tolerance=1e-2):
            """ Calculates the cumulative sum to determine if metric data (MMI) has plateaud for given level """
            flattened_data = np.array(criteria_data).flatten()
            if len(flattened_data) < window_size:
                return True

            cumsum_diff = np.cumsum(np.abs(np.diff(flattened_data)))
            window_diff = np.diff(cumsum_diff)
            
            for i in range(len(window_diff) - window_size + 1):
                if np.allclose(window_diff[i:i + window_size], 0, atol=tolerance):
                    return False
                
            return True

        """ Try to stretch image and eliminate background  """
        # self.moving_mask, self.fixed_mask = self.graphobjoh.plot_surface(volume1 = self.moving_image, volume2 = self.fixed_image, pull_binary_mask = True)
        # self.moving_mask = binary_fill_holes(self.moving_mask)
        # structure = np.ones((10, 10, 10))
        # dialed_moving_mask = binary_dilation(self.moving_mask, structure=structure)
        # eroded_moving_mask = binary_erosion(self.moving_mask, structure=structure)
        # outline_moving_mask = dialed_moving_mask ^ eroded_moving_mask 
        # self.moving_image = np.where(outline_moving_mask, self.moving_image, 0)
        # self.moving_mask, paremeters = manual_find_axes_sampling(self.fixed_mask, self.moving_mask, drop_dir=self.drop_path, best_params=None)
        # self.moving_image = zoom(self.moving_image, (paremeters[0], paremeters[1], paremeters[2])) 

        # slice_views(array1 = self.moving_image, 
        #             array2 = self.fixed_image, 
        #             output_filename=os.path.join(self.drop_path,f'pre_cutstretched_arrays2.jpg'), 
        #             image_type='max')

        # Convert arrays to SimpleITK images
        fixed = sitk.GetImageFromArray(self.fixed_image) if isinstance(self.fixed_image, np.ndarray) else self.fixed_image
        moving = sitk.GetImageFromArray(self.moving_image) if isinstance(self.moving_image, np.ndarray) else self.moving_image

        # Convert to 32 float
        fixed = sitk.Cast(fixed, sitk.sitkFloat32)
        moving = sitk.Cast(moving, sitk.sitkFloat32)

        # Blur images and plot
        sfixed = sitk.SmoothingRecursiveGaussian(fixed, sigma=4.0)
        smoving = sitk.SmoothingRecursiveGaussian(moving, sigma=3.0)
        slice_views(array1=sitk.GetArrayFromImage(smoving), 
                    array2 = sitk.GetArrayFromImage(sfixed), 
                    output_filename=os.path.join(self.drop_path,f'blurred_images_{self.time_to_str()}.jpg'), 
                    image_type='max')
         
        if resolutions is None:
            resolutions = [100.0, 90.0, 80.0, 70.0, 60.0, 50.0, 40.0, 30.0, 20.0] 
        
        if iters is None:
            iters = [10, 10, 10, 10, 10, 10, 10, 10, 10] 

        tolerances_oh = [0.1, 0.1, 0.1, 0.01, 0.01, 0.001, 0.0001, 0.00001, 0.000001]

        criteria_results = []
        for k,(resolution, nits) in enumerate(zip(resolutions,iters)):
            search_string = os.path.join(self.drop_path, f"nonrigid_transform_resolution*_attempt*_step*.pkl")
            found_files = glob.glob(search_string)
            smallest_resolution = None #default value

            if not found_files:
                current_transform = None
                print('No transform files found')
            
            else:
                # Collect all resolution data for saved files
                found_files_resolutions=[]
                for file in found_files:
                    _, data = file.split('resolution')
                    resolution_oh, _ = data.split('_attempt')
                    found_files_resolutions.append([int(resolution_oh)])
                
                # Determine smallest resolution in list
                found_files_resolutions = np.array(found_files_resolutions)
                smallest_resolution = found_files_resolutions[np.argmin(found_files_resolutions)][0]

                # Update found files to match the current resolution
                if int(resolution)>int(smallest_resolution):
                    continue
                
                elif int(resolution)<=int(smallest_resolution):
                    new_search_string = os.path.join(self.drop_path, f"nonrigid_transform_resolution{smallest_resolution}_attempt*_step*.pkl")
                    smallest_found_files = glob.glob(new_search_string)
                else:
                    raise ValueError("smallest_resolution does not align with any resolutions")
                
                # Get the last file (max number) and load it as current_transform
                values = []
                for file in smallest_found_files:
                    _, numberdata = file.split('attempt')
                    numberoh, _ = numberdata.split('_step')
                    values.append(int(numberoh))

                values = np.array(values)
                last_file = found_files[np.argmax(values)]

                print(f'Using {last_file} as current transform')
                with open(last_file, "rb") as f:
                    current_transform = pickle.load(f)

            if smallest_resolution == resolution:
                continue

            learning=True
            attempt_oh = 0
            while learning:
                print(f'Alignment resolution {resolution} for attempt {attempt_oh}')
                mmi_results, current_transform = alignoh(resolution, nits, sfixed, smoving, 
                                                         iteration_number = k, attempt = attempt_oh, 
                                                         current_transform=current_transform, transform_file="transform.pkl")
                criteria_results.append(mmi_results)
                learning = plateau_cumsum(criteria_results,tolerance=tolerances_oh[k])
                
                # Plot current transformed image
                resampler = sitk.ResampleImageFilter()
                resampler.SetSize(moving.GetSize())
                resampler.SetOutputSpacing(moving.GetSpacing())
                resampler.SetOutputOrigin(moving.GetOrigin())
                resampler.SetOutputDirection(moving.GetDirection())
                resampler.SetTransform(current_transform)  # Apply the current transform to the moving image
                transformed_image = resampler.Execute(moving)

                # Plot image of current attempt
                slice_views(array1=sitk.GetArrayFromImage(transformed_image),
                            array2 = sitk.GetArrayFromImage(sfixed), 
                            output_filename=os.path.join(self.drop_path,f'mulitresolution_alignment_resolution{resolution}_step{k}_attempt{attempt_oh}.jpg'), 
                            image_type='max', overlay=True)
                
                attempt_oh+=1
            
            if current_transform is None:
                raise ValueError("current_transform is None.")

            smoving = sitk.Resample(smoving, sfixed, current_transform, sitk.sitkLinear, 0.0, moving.GetPixelID())
            
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

    def time_to_str(self):
        now = datetime.now()
        return now.strftime("%Y_%m_%d_%H_%M_%S")
    
    def __call__(self):
        # Preprocess image volumes ... eliminate high signal
        print('Replace high signal values to prevent misalignments...')
        slice_views(array1=self.moving_array_original, array2=self.target_array, output_filename=os.path.join(self.drop_path,"pre_highsignal_replace.jpg"))
        self.moving_array_original = replace_signal(volume=self.moving_array_original) 
        self.target_array = replace_signal(volume = self.target_array, normalize=True)
        slice_views(array1=self.moving_array_original, array2=self.target_array, output_filename=os.path.join(self.drop_path,"post_highsignal_replace.jpg"))

        # Zero pad both arrays for consistent dimensions
        print('Zero padding data...')
        self.moving_array_original, self.target_array = zero_pad_arrays(array1=self.moving_array_original, array2=self.target_array)
        _, self.annotation_array_original = zero_pad_arrays(array1=self.moving_array_original, array2=self.annotation_array)
    
        # Binary mask alignment and stretching/squeezing
        if self.align_binary_mask:
            print('Performing alingment and stretching on binary masks of data...')
            self.moving_mask, self.target_mask = self.graphobjoh.plot_surface(volume1 = self.moving_array_original, 
                                        volume2 = self.target_array, pull_binary_mask = True) # Get binary masks
            
            slice_views(array1=self.moving_mask, array2=self.target_mask, output_filename=os.path.join(self.drop_path,"firstbinarymasks.jpg"))

            best_params_mask_file = os.path.join(self.drop_path, f"rigid_transform_step1.pkl")
            best_params_mask_stretch_file = os.path.join(self.drop_path, f"rigid_stretch_transform_step2.pkl")
            if os.path.exists(best_params_mask_file):
                """ If real, load in best rigid parameters """
                print(f"Bayes Opt file previously calculated for mask, loading file ...")
                with open(best_params_mask_file, "rb") as f:
                    self.best_params_mask_oh = pickle.load(f)

                with open(best_params_mask_stretch_file, "rb") as f:
                    self.best_params_mask_stretch_oh = pickle.load(f)
            else:
                """ If no file exists, perform rigid transform via bayes search """
                print('Performing Bayesian-based rigid transformation ... ') 
                self.fixed_mask, self.moving_mask, self.best_params_mask_oh = find_affine_matrix(fixed_image=self.target_mask,
                                                                                                moving_image=self.moving_mask,
                                                                                                best_params=self.best_params_mask_oh, 
                                                                                                drop_dir = self.drop_path,
                                                                                                ntrials=10000)
                
                self.moving_mask, self.best_params_mask_stretch_oh = manual_find_axes_sampling(self.fixed_mask,
                                                                                            self.moving_mask,
                                                                                            drop_dir=self.drop_path,
                                                                                            best_params=self.best_params_mask_stretch_oh)

                with open(best_params_mask_file, "wb") as f:
                    pickle.dump(self.best_params_mask_oh, f)
                    print('Saved BayesOpt best parameters rigid mask ...')

                with open(best_params_mask_stretch_file, "wb") as f:
                    pickle.dump(self.best_params_mask_stretch_oh, f)
                    print('Saved BayesOpt best parameters stretch mask ...')

            # Apply alignment to data 
            print('Applying binary mask transformations to original data ...')
            assert self.best_params_mask_oh is not None
            assert self.best_params_mask_stretch_oh is not None

            # Filter background data
            self.moving_mask = binary_fill_holes(self.moving_mask)
            structure = np.ones((3, 3, 3))
            self.dialed_moving_mask = binary_dilation(self.moving_mask, structure=structure)
            self.moving_array_original = np.where(self.dialed_moving_mask == 0, 0, self.moving_array_original)

            slice_views(array1=self.moving_array_original,
                        array2=self.moving_mask,
                        output_filename=os.path.join(self.drop_path,'filtered_out_usingmask.jpg'), 
                        image_type='mean')

            # Perform rigid alignment
            best_affine_transform = sitk.AffineTransform(3)
            best_affine_transform = set_affine_rotation(best_affine_transform, self.best_params_mask_oh['theta_x'], self.best_params_mask_oh['theta_y'], self.best_params_mask_oh['theta_z'])
            best_affine_transform.SetTranslation([self.best_params_mask_oh['translation_x'], self.best_params_mask_oh['translation_y'], self.best_params_mask_oh['translation_z']])
            best_affine_transform.Scale(self.best_params_mask_oh['scale'])
            best_resampler = sitk.ResampleImageFilter()
            best_resampler.SetSize(sitk.GetImageFromArray(self.target_array.astype(np.float32)).GetSize())
            best_resampler.SetOutputSpacing(sitk.GetImageFromArray(self.target_array.astype(np.float32)).GetSpacing())
            best_resampler.SetTransform(best_affine_transform)
            best_resampler.SetInterpolator(sitk.sitkLinear)
            best_aligned_image = best_resampler.Execute(sitk.GetImageFromArray(self.moving_array_original.astype(np.float32)))
            self.moving_image = sitk.GetArrayFromImage(best_aligned_image)
            self.fixed_image = self.target_array
            
            try:
                self.moving_image = zoom(self.moving_image, (self.best_params_mask_stretch_oh[0], self.best_params_mask_stretch_oh[1], self.best_params_mask_stretch_oh[2])) 
            except:
                raise(" Must change previous line if using bayes opt for stretching code")
            self.moving_image = adjust_volume_shape(volume=self.moving_image,target_shape = self.fixed_image.shape)

            slice_views(array1=self.moving_image,
                        array2=self.fixed_image,
                        output_filename=os.path.join(self.drop_path,'orig_moving_image_post.jpg'), 
                        image_type='max')
            
        else:
            self.moving_image = self.moving_array_original
            self.fixed_image = self.target_array
     
        # Perform Rigid Alignment on original data 
        self.moving_image = self.moving_image.astype(np.float32)
        self.fixed_image = self.fixed_image.astype(np.float32)

        print('Non-rigid alignment of orignal data ...')
        best_params_file = os.path.join(self.drop_path, f"rigid_transform_step3.pkl")
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
            best_resampler.SetSize(sitk.GetImageFromArray(self.target_array.astype(np.float32)).GetSize())
            best_resampler.SetOutputSpacing(sitk.GetImageFromArray(self.target_array.astype(np.float32)).GetSpacing())
            best_resampler.SetTransform(best_affine_transform)
            best_resampler.SetInterpolator(sitk.sitkLinear)
            best_aligned_image = best_resampler.Execute(sitk.GetImageFromArray(self.moving_array_original.astype(np.float32)))
            self.moving_image = sitk.GetArrayFromImage(best_aligned_image)
            self.fixed_image = self.target_array

        else:
            """ If no file exists, perform rigid transform via bayes search """
            print('Performing Bayesian-based rigid transformation ... ') 
            self.fixed_image, self.moving_image, self.best_params_oh = find_affine_matrix(fixed_image=self.fixed_image,
                                                                    moving_image=self.moving_image,
                                                                    best_params=self.best_params_oh, 
                                                                    drop_dir = self.drop_path,
                                                                    ntrials=10000)
            
            with open(best_params_file, "wb") as f:
                pickle.dump(self.best_params_oh, f)
                print('Saved BayesOpt best parameters ...')

        # Perform non-rigid alignment
        print('Performing Non-Rigid Multiresolution Alignment ... ') 
        self.fixed_image = self.fixed_image.astype(np.float32) if self.fixed_image.dtype == np.float16 else self.fixed_image
        self.moving_image = self.moving_image.astype(np.float32) if self.moving_image.dtype == np.float16 else self.moving_image

        starting_mmi = MMI(sitk.GetImageFromArray(self.fixed_image),sitk.GetImageFromArray(self.moving_image))
        print(f' The MMI prior to nonrigid alignment is {starting_mmi}')
        self.nonrigid_moving_image = self.multiresolution_align()

def cli_parser():
    """ Takes command line inputs and parses them for downstream """
    parser = argparse.ArgumentParser()
    parser.add_argument('--image_path',type=str,help='Full path to best qualtiy light sheet images for registration ...')
    parser.add_argument('--atlas_path',type=str,help="Full path to folder containing atlas. If folder is empty, atlas is downloaded")
    parser.add_argument('--output_path',type=str,help='Full path containin results. Path will be appended with subfolder containing current date and time. \
                        These subfolders are where data will be saved.')
    parser.add_argument('--full_output_path', action='store_true', help = 'a full path to output_path')
    parser.add_argument('--align_binary_mask', default=None, action='store_true')
    parser.add_argument('--crop_border_noise_bool', default=None, action='store_true')

    parser.add_argument("--force_orientation", nargs='*', type=int, default=None,
                        help="Optional: 3 integers defining forced orientation (or omitted)")
    parser.add_argument("--force_flips", nargs='*', type=int, default=None,
                        help="Optional: 3 integers defining forced flips (or omitted)")

    args = parser.parse_args()

    # Convert empty lists to None (when the flag is present but no numbers are given)
    if args.force_orientation == []:
        args.force_orientation = None

    if args.force_flips == []:
        args.force_flips = None

    # Ensure valid input for exactly 3 values
    if args.force_orientation is not None and len(args.force_orientation) != 3:
        parser.error("--force_orientation must have exactly 3 values or be omitted.")
    if args.force_flips is not None and len(args.force_flips) != 3:
        parser.error("--force_flips must have exactly 3 values or be omitted.")

    print(args.output_path)
    print(f"Force flips is set to {args.force_flips}")
    print(f"Force orientation is set to {args.force_orientation}")
    print(f"Align binary mask is set to {args.align_binary_mask}")
    print(f"Crop border noise is set to {args.crop_border_noise_bool}")

    # Get current time as string and generate output folder
    now = datetime.now()
    init_date_time= now.strftime("%Y_%m_%d_%H_%M_%S")
    if args.full_output_path:
        output_path = args.output_path

    else:
        new_folder = f'current_run_{init_date_time}'
        output_path = os.path.join(args.output_path,new_folder)
        if not os.path.exists(output_path): 
            os.makedirs(output_path)

    # Append a few new arguments
    args.output_path = output_path
    args.init_date_time = init_date_time
    return args

def main(args):
    # Update classes to have matching methods
    MovingImage.generate_gif = target.generate_gif 
    alignment.generate_gif = target.generate_gif 

    # Generate target and MovingImage objects
    target_oh = target(target_path=args.atlas_path)
    target_oh()

    Image_oh = MovingImage(image_path = args.image_path, drop_path=args.output_path, force_orientations=args.force_orientation, force_flips=args.force_flips, crop_border_noise_bool = args.crop_border_noise_bool)
    Image_oh()

    Image_oh.generate_gif(volume=Image_oh.downsampled_volume,full_filename=os.path.join(args.output_path,f'init_moving_array_{args.init_date_time}.gif'))
    Image_oh.generate_gif(volume=target_oh.template,full_filename=os.path.join(args.output_path,f'init_target_array_{args.init_date_time}.gif'))    

    # Perform alignment
    graphobj = volume_graphics()
    alignment_object = alignment(MovingImageObject=Image_oh, TargetImageObject=target_oh, graphobjoh = graphobj, drop_path=args.output_path, align_binary_mask=args.align_binary_mask)
    alignment_object() 

    # Save most important arrays
    np.save(os.path.join(args.output_path,'downsampled_volume.npy'), Image_oh.downsampled_volume) # The original downsampled array without padding
    np.save(os.path.join(args.output_path,'template_volume.npy'), target_oh.template) # The orignal atlas without padding as np array
    np.save(os.path.join(args.output_path,'moving_array_original.npy'), alignment_object.moving_array_original) # The original array with zero padding
    np.save(os.path.join(args.output_path,'nonrigid_moving_image.npy'), alignment_object.nonrigid_moving_image) # The final array after alignment
    np.save(os.path.join(args.output_path,'target_array.npy'), alignment_object.target_array) # The target array with zero padding

    # Determine if cell coordinates are real and run cell alignment code if true
    cell_count_files = glob.glob(os.path.join(args.output_path,'*cell_counts*csv'))
    if len(cell_count_files)>0:
        # Zero pad the atlas
        zp_id_atlas_oh = zero_pad_arrays(array1 = target_oh.annotation, array2 = alignment_object.target_array)
        
        # Create cell alignment object
        cell_alignment_obj = cellalignment(zp_id_atlas = zp_id_atlas_oh, 
                                        zp_template_atlas = alignment_object.target_array, 
                                        ds_zp_transformed_moving_image = alignment_object.nonrigid_moving_image, 
                                        drop_path = alignment_object.drop_path) # create the object
        
        # Update coordinate system data regarding dimensions
        new_x_dim, new_y_dim, new_z_dim = alignment_object.nonrigid_moving_image.shape
        original_x_dim, original_y_dim, original_z_dim = Image_oh.orig_x_dim, Image_oh.orig_y_dim, Image_oh.orig_z_dim
        cell_alignment_obj.update_coordinate_systems(new_x_dim, new_y_dim, new_z_dim, original_x_dim, original_y_dim, original_z_dim) # add the coordinate system data
        
        # Run pipeline
        cell_alignment_obj() 
    
    else:
        print("No cell count files found, skipping cell count alignment")

    return 
   
if __name__=='__main__':
    args = cli_parser()
    main(args)