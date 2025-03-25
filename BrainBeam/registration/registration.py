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
import matplotlib.pyplot as plt
import glob
from scipy.ndimage import zoom, binary_dilation, binary_fill_holes
import SimpleITK as sitk
from BrainBeam.registration.padding import zero_pad_arrays
from BrainBeam.registration.BayesRigidTransform import find_affine_matrix, set_affine_rotation, manual_find_axes_sampling, adjust_volume_shape, MMI
from BrainBeam.registration.graphics import slice_views
from BrainBeam.registration.preprocess import replace_signal, flatten_list
from datetime import datetime
import time
import pickle
import warnings
warnings.simplefilter("ignore")

# Set max hyper threading
max_threads = os.cpu_count()
sitk.ProcessObject.SetGlobalDefaultNumberOfThreads(max_threads)

class alignment:
    def __init__(self, MovingImageObject, TargetImageObject, logger, drop_path, graphobjoh=None, align_binary_mask=False):
        # Set up objects as attributes
        self.MovingImageObject = MovingImageObject
        self.TargetImageObject = TargetImageObject
        self.logger = logger
        self.drop_path = drop_path

        # Parameter attributes for alignment
        self.best_params_oh = None # Default assumption
        self.best_params_mask_oh = None
        self.best_params_mask_stretch_oh = None

        # Pull out the original moving array, target image etc as new attributes 
        self.moving_array_original = self.MovingImageObject.downsampled_volume.astype(np.float64)
        self.target_array = self.TargetImageObject.template.astype(np.float64)
        self.annotation_array = self.TargetImageObject.annotation.astype(np.float64)
        self.graphobjoh = graphobjoh
        
        # Determine if binary mask is present. 
        if align_binary_mask is None:
            align_binary_mask = False
        self.align_binary_mask = align_binary_mask
        
    def multiresolution_align(self,  resolutions=None, iters=None):
        """ Multi-Resolution Alignment -- 
            Used for aligning two image volumes for light sheet imaging data.  """

        def alignoh(resolution, previous_resolution, nits, fixed, moving, iteration_number, attempt=0, 
            current_transform=None, transform_file="transform.pkl", mmi_results=None):
            """Runs alignment and collects MMI data for each trial."""
            self.logger.info(f"Resolution: {resolution}, Iterations: {nits}")

            all_mmi_values = []  # Store metric values at each iteration

            def update_mmi():
                """Callback function to store metric value at each iteration."""
                all_mmi_values.append(registration_method.GetMetricValue())

            # Construct transform filename
            name, fileend = transform_file.split('.')
            transform_file = os.path.join(self.drop_path,f"nonrigid_{name}_resolution{int(resolution)}_attempt{attempt}_step{iteration_number}.{fileend}")

            # Compute B-spline grid size
            grid_physical_spacing = [resolution] * 3
            image_physical_size = [size * spacing for size, spacing in zip(fixed.GetSize(), fixed.GetSpacing())]
            grid_size = [int(image_physical_size[i] / grid_physical_spacing[i] + 0.5) for i in range(3)]
            transform_domain_mesh_size = [max(1, grid_size[i] - 3) for i in range(3)]
            self.logger.info(f"Mesh size: {transform_domain_mesh_size}")

            # Initialize list to store MMI data
            if mmi_results is None:
                mmi_results = []

            # Initialize or update the transform
            if current_transform is None:
                self.logger.info("Initializing new B-spline transform...")
                init_transform = sitk.BSplineTransformInitializer(fixed, transformDomainMeshSize=transform_domain_mesh_size, order=3)

            else:
                self.logger.info("Using existing transform...")
                init_transform = sitk.BSplineTransformInitializer(fixed, transformDomainMeshSize=transform_domain_mesh_size, order=3)
                init_transform.SetFixedParameters(current_transform.GetFixedParameters())  
                init_transform.SetParameters(current_transform.GetParameters())  

            # Set up the registration method
            registration_method = sitk.ImageRegistrationMethod()
            registration_method.SetMetricAsMattesMutualInformation(numberOfHistogramBins=100)
            registration_method.SetMetricSamplingStrategy(registration_method.RANDOM)
            registration_method.SetMetricSamplingPercentage(1.0)
            registration_method.SetOptimizerAsLBFGSB(numberOfIterations=nits)
            registration_method.SetOptimizerScalesFromPhysicalShift()
            registration_method.SetInitialTransform(init_transform, inPlace=False)

            # Add command to collect MMI values at each iteration
            registration_method.AddCommand(sitk.sitkIterationEvent, update_mmi)

            # Execute registration
            current_time = time.localtime()
            formatted_time = time.strftime("%I:%M %p", current_time)
            self.logger.info(f"Starting registration at {formatted_time}...")
            current_transform = registration_method.Execute(fixed, moving)

            # Store and compare MMI values
            final_mmi_value = registration_method.GetMetricValue()
            self.logger.info(f"Final MMI value: {final_mmi_value}")

            if mmi_results:
                prev_mmi = mmi_results[-1]
                self.logger.info(f"Previous MMI: {prev_mmi}, Difference: {final_mmi_value - prev_mmi}")

            mmi_results.append(all_mmi_values)

            # Save transform
            self.logger.info("Saving transform into a file!")
            with open(transform_file, "wb") as f:
                pickle.dump(current_transform, f)
                self.logger.info(f"Transform saved to {transform_file}.")

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
        
        """ Start of Alignment """
        self.logger.info('Setting up multiresolution alignment, generating global variables and call back command ... ')

        # Convert arrays to SimpleITK images
        fixed = sitk.GetImageFromArray(self.fixed_image) if isinstance(self.fixed_image, np.ndarray) else self.fixed_image
        moving = sitk.GetImageFromArray(self.moving_image) if isinstance(self.moving_image, np.ndarray) else self.moving_image

        # Convert to 32 float
        fixed = sitk.Cast(fixed, sitk.sitkFloat32)
        moving = sitk.Cast(moving, sitk.sitkFloat32)

        # Blur images and plot
        sfixed = sitk.SmoothingRecursiveGaussian(fixed, sigma=4.0)
        smoving = sitk.SmoothingRecursiveGaussian(moving, sigma=3.0)
        slice_views(array1=sitk.GetArrayFromImage(smoving), array2 = sitk.GetArrayFromImage(sfixed), 
                    output_filename=os.path.join(self.drop_path,f'blurred_images_{self.time_to_str()}.jpg'), 
                    image_type='max')
         
        # Set up resolutions, iterations, and tolerances
        resolutions = [100.0, 90.0, 80.0, 70.0, 60.0, 50.0, 40.0] #, 30.0] 
        iters = [10, 10, 10, 10, 10, 10, 10 ] #, 10] 
        tolerances_oh = [0.1, 0.1, 0.1, 0.01, 0.01, 0.001, 0.0001 ]#, 0.00001]

        # Create empty list for recording alignment MMI metrics
        criteria_results = []

        # Loop over resolution and iteration values
        previous_resolution = resolutions[0]
        for k,(resolution_oh, nits) in enumerate(zip(resolutions,iters)):
            search_string = os.path.join(self.drop_path, f"nonrigid_transform_resolution*_attempt*_step*.pkl")
            found_files = glob.glob(search_string)

            smallest_resolution = None
            current_transform = None

            if not found_files:
                self.logger.info("No transform files found")
            
            else:
                # Extract resolution and attempt from filenames
                resolution_attempt_map = {}

                for file in found_files:
                    try:
                        _, data = file.split('resolution')
                        resolution_str, attempt_data = data.split('_attempt')
                        attempt_str, _ = attempt_data.split('_step')

                        resolution = int(resolution_str)
                        attempt = int(attempt_str)

                        if resolution not in resolution_attempt_map:
                            resolution_attempt_map[resolution] = []

                        resolution_attempt_map[resolution].append((attempt, file))

                    except ValueError:
                        self.logger.error(f"Skipping malformed filename: {file}")

                # Sort resolutions and find the smallest one with a valid attempt
                sorted_resolutions = sorted(resolution_attempt_map.keys())
    
                for res in sorted_resolutions:
                    attempt_file_list = resolution_attempt_map[res]
                    best_attempt_file = max(attempt_file_list, key=lambda x: x[0])[1]  # Get file with highest attempt

                    # Set the smallest resolution only if there was at least one attempt
                    if smallest_resolution is None or res < smallest_resolution:
                        smallest_resolution = res
                        self.logger.info(f"Using {best_attempt_file} as current transform")
                        with open(best_attempt_file, "rb") as f:
                            current_transform = pickle.load(f)

                    # If we have found the first valid transform, break the loop
                    if smallest_resolution is not None:
                        break  

            # Ensure skipping logic is correct
            if smallest_resolution is not None and int(resolution_oh)>=int(smallest_resolution):
                previous_resolution = resolution_oh
                continue  # Skip higher resolutions since a smaller one already has an attempt
            
            try:
                attempt_oh = 0 + int(attempt) + 1
            except:
                attempt_oh = 0

            learning=True
            while learning:
                self.logger.info(f'Alignment resolution {resolution_oh} for attempt {attempt_oh}')
                mmi_results, current_transform = alignoh(resolution_oh, previous_resolution, nits, sfixed, smoving, 
                                                         iteration_number = k, attempt = attempt_oh, 
                                                         current_transform=current_transform, transform_file="transform.pkl")
                
                # Append to larger list and flatten
                criteria_results.append(mmi_results)
                criteria_results = flatten_list(criteria_results)
    
                # Determine if learning has plateau'd 
                learning = plateau_cumsum(criteria_results,tolerance=tolerances_oh[k])
                
                # Apply the current B-spline transform to the moving image (smoving)
                smoving_for_plot = sitk.Resample(smoving, sfixed, current_transform, sitk.sitkLinear, 0.0, smoving.GetPixelID())

                # Plot image of current attempt
                slice_views(array1=sitk.GetArrayFromImage(smoving_for_plot),
                            array2 = sitk.GetArrayFromImage(sfixed), 
                            output_filename=os.path.join(self.drop_path,f'mulitresolution_alignment_resolution{resolution_oh}_step{k}_attempt{attempt_oh}.jpg'), 
                            image_type='max', overlay=True)
                
                attempt_oh+=1
            
            if current_transform is None:
                raise ValueError("current_transform is None.")
            
            previous_resolution = resolution_oh
            
        plt.figure()
        plt.plot(criteria_results)
        plt.savefig(os.path.join(self.drop_path,"MMIresultsall.jpg"))

        # Apply the final transformation to the moving image
        self.logger.info('Applying final transformation to moving image ...')
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
    
    def align_with_binary_mask(self):
        # Binary mask alignment and stretching/squeezing
        if self.align_binary_mask:
            self.logger.info('Performing alingment and stretching on binary masks of data...')
            self.moving_mask, self.target_mask = self.graphobjoh.plot_surface(volume1 = self.moving_array_original, 
                                        volume2 = self.target_array, pull_binary_mask = True) # Get binary masks
            
            slice_views(array1=self.moving_mask, array2=self.target_mask, output_filename=os.path.join(self.drop_path,"firstbinarymasks.jpg"))

            best_params_mask_file = os.path.join(self.drop_path, f"rigid_transform_step1.pkl")
            best_params_mask_stretch_file = os.path.join(self.drop_path, f"rigid_stretch_transform_step2.pkl")
            if os.path.exists(best_params_mask_file):
                """ If real, load in best rigid parameters """
                self.logger.info(f"Bayes Opt file previously calculated for mask, loading file ...")
                with open(best_params_mask_file, "rb") as f:
                    self.best_params_mask_oh = pickle.load(f)

                with open(best_params_mask_stretch_file, "rb") as f:
                    self.best_params_mask_stretch_oh = pickle.load(f)
            else:
                """ If no file exists, perform rigid transform via bayes search """
                self.logger.info('Performing Bayesian-based rigid transformation ... ') 
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
                    self.logger.info('Saved BayesOpt best parameters rigid mask ...')

                with open(best_params_mask_stretch_file, "wb") as f:
                    pickle.dump(self.best_params_mask_stretch_oh, f)
                    self.logger.info('Saved BayesOpt best parameters stretch mask ...')

            # Apply alignment to data 
            self.logger.info('Applying binary mask transformations to original data ...')
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
                self.logger.error("Must change previous line if using bayes opt for stretching code")
                raise(" Must change previous line if using bayes opt for stretching code")
            self.moving_image = adjust_volume_shape(volume=self.moving_image,target_shape = self.fixed_image.shape)

            slice_views(array1=self.moving_image,
                        array2=self.fixed_image,
                        output_filename=os.path.join(self.drop_path,'orig_moving_image_post.jpg'), 
                        image_type='max')
            
        else:
            self.moving_image = self.moving_array_original
            self.fixed_image = self.target_array

    def __call__(self):
        # Preprocess image volumes ... eliminate high signal
        self.logger.info('Replace high signal values to prevent misalignments...')
        slice_views(array1=self.moving_array_original, array2=self.target_array, output_filename=os.path.join(self.drop_path,"pre_highsignal_replace.jpg"))
        self.moving_array_original = replace_signal(volume=self.moving_array_original) 
        self.target_array = replace_signal(volume = self.target_array, normalize=True)
        slice_views(array1=self.moving_array_original, array2=self.target_array, output_filename=os.path.join(self.drop_path,"post_highsignal_replace.jpg"))

        # Zero pad both arrays for consistent dimensions
        self.logger.info('Zero padding data...')
        self.moving_array_original, self.target_array = zero_pad_arrays(array1=self.moving_array_original, array2=self.target_array)
        _, self.annotation_array_original = zero_pad_arrays(array1=self.moving_array_original, array2=self.annotation_array)
    
        # Determine whether to align using a binary mask
        self.align_with_binary_mask()
     
        # Perform Rigid Alignment on original data 
        self.moving_image = self.moving_image.astype(np.float32)
        self.fixed_image = self.fixed_image.astype(np.float32)

        self.logger.info('Non-rigid alignment of orignal data ...')
        best_params_file = os.path.join(self.drop_path, f"rigid_transform_step3.pkl")
        if os.path.exists(best_params_file):
            """ If real, load in best rigid parameters """
            self.logger.info(f"Bayes Opt file previously calculated, loading file ...")
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
            self.logger.info('Performing Bayesian-based rigid transformation ... ') 
            self.fixed_image, self.moving_image, self.best_params_oh = find_affine_matrix(fixed_image=self.fixed_image,
                                                                    moving_image=self.moving_image,
                                                                    best_params=self.best_params_oh, 
                                                                    drop_dir = self.drop_path,
                                                                    ntrials=10000)
            
            with open(best_params_file, "wb") as f:
                pickle.dump(self.best_params_oh, f)
                self.logger.info('Saved BayesOpt best parameters ...')

        # Perform non-rigid alignment
        self.logger.info('Performing Non-Rigid Multiresolution Alignment ... ') 
        self.fixed_image = self.fixed_image.astype(np.float32) if self.fixed_image.dtype == np.float16 else self.fixed_image
        self.moving_image = self.moving_image.astype(np.float32) if self.moving_image.dtype == np.float16 else self.moving_image

        starting_mmi = MMI(sitk.GetImageFromArray(self.fixed_image),sitk.GetImageFromArray(self.moving_image))
        self.logger.info(f' The MMI prior to nonrigid alignment is {starting_mmi}')
        self.nonrigid_moving_image = self.multiresolution_align()
