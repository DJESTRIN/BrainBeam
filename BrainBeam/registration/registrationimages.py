#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: RegistrationImages.py
Description: Registration Image classes
Author: David Estrin
Date: 2024-12-11
Version: 1.0
"""
# Import dependencies
import numpy as np
import os
import pandas as pd
from allensdk.core.reference_space_cache import ReferenceSpaceCache
from pathlib import Path
from scipy.ndimage import distance_transform_edt
import matplotlib.pyplot as plt
from PIL import Image
import glob
import tifffile as tiff
import tqdm
import SimpleITK as sitk
from BrainBeam.registration.graphics import slice_views
from BrainBeam.registration.preprocess import determine_doublecount_points 
import warnings
import ipdb
warnings.simplefilter("ignore")

# Set max hyper threading
max_threads = os.cpu_count()
sitk.ProcessObject.SetGlobalDefaultNumberOfThreads(max_threads)

def normalize_to_255(volume):
    volume = volume.astype(np.float32, copy=False)
    min_value = volume.min()
    max_value = volume.max()
    if max_value == min_value:
        return np.zeros_like(volume, dtype=np.float32)
    return ((volume - min_value) / (max_value - min_value)) * 255

# Custom classes and functions
class TargetImage:
    def __init__(self, target_path, logger, voxelsize=50, visualize=True):
        self.target_path = target_path
        self.logger = logger
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
        avs = [mean_intensity_x, mean_intensity_y, mean_intensity_z]

        # Find the AP axis and determine whether it needs to be flipped
        longest_dim = np.where(av_szs == av_szs.max())
        
        AP = avs[longest_dim[0][0]]
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
        previous_dims = {int(longest_dim[0][0]), int(mirror_dim[0][0])}
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
        self.annotation_transposed = np.transpose(self.annotation, (int(mirror_dim[0]), int(leftover_dim), int(longest_dim[0]))) 

        if SP_flip == -1:
            self.template_transposed = self.template_transposed[:, ::-1, :]  # Flip the second axis (A)
            self.annotation_transposed = self.annotation_transposed[:, ::-1, :]  # Flip the second axis (A)
        if AP_flip == -1:
            self.template_transposed = self.template_transposed[:, :, ::-1]  # Flip the third axis (R)
            self.annotation_transposed = self.annotation_transposed[:, :, ::-1]  # Flip the third axis (R)

        self.template = self.template_transposed
        self.annotation = self.annotation_transposed

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
        self.template = normalize_to_255(self.template)

    def __call__(self):
        self.logger.info('Generating target image from ARA. Downloading now if not already downloaded.')
        self.download_atlas()
        self.download_template()

        self.logger.info('Determine ARA orientation.')
        self.determine_orientation()

        self.logger.info('Normalize ARA .')
        self.normalize_template_stack()

        if self.visualize:
            self.logger.info('Generate gif of ARA.')
            self.generate_gif(volume=self.template,full_filename=os.path.join(self.target_path,'template.gif'))
            self.generate_gif(volume=self.annotation,full_filename=os.path.join(self.target_path,'annotation.gif'))

        self.logger.info('Finished with target image object.')

class MovingImage:
    def __init__(self, image_path, drop_path, logger, voxel_size=np.array([2,2.3,2.3]), ds_voxelsize=50, 
                 force_orientations=None, force_flips=None, crop_border_noise_bool=False):
        self.image_path = image_path
        self.target_size = ds_voxelsize
        self.voxel_size = voxel_size
        self.drop_path = drop_path 
        self.logger = logger
        self.force_orientations = force_orientations
        self.force_flips = force_flips
        self.crop_border_noise_bool = crop_border_noise_bool

    def __call__(self):
        self.logger.info('Loading in images')
        self.get_image_list()

        self.logger.info('Grabbing MI medidata ')
        self.grab_original_image_medidata()

        self.logger.info('Downsample image stack')
        self.downsample(output_filename=os.path.join(self.drop_path,'downsampled_moving_image.tiff'))

        self.logger.info('Grabbing MI medidata for DS image')
        self.grab_ds_image_medidata()
        
        self.logger.info('Normalize Image stack')
        self.normalize_image_stack()

        self.logger.info('Adjusting brightness')
        self.downsampled_volume = self.adjust_brightness(stack_oh = self.downsampled_volume)

        self.logger.info('Determine MI orientation!')
        self.downsampled_volume = self.determine_orientation()

        if self.crop_border_noise_bool:
            self.logger.info('Cropping border of image')
            self.downsampled_volume = self.crop_border_noise(stack_oh = self.downsampled_volume, distance_threshold=10, artificial_padding=5)

        self.logger.info('Clipping high signal')
        self.downsampled_volume = self.clip_high_signal(stack_oh = self.downsampled_volume)

        self.logger.info('Finished generating MI')

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
            else:
                self.downsampled_volume_transposed = self.downsampled_volume.copy() # Written as a quick fix  03/10/2025

            self.logger.info(f'This is what force flips is set to inside moving image: {self.force_flips}')
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
            avs = [mean_intensity_x, mean_intensity_y, mean_intensity_z]

            # Find the AP axis and determine whether it needs to be flipped
            longest_dim = np.where(av_szs == av_szs.max())
            
            AP = avs[longest_dim[0][0]]
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
            previous_dims = {int(longest_dim[0][0]), int(mirror_dim[0][0])}
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
            self.downsampled_volume_transposed = np.transpose(self.downsampled_volume, (int(mirror_dim[0][0]), int(leftover_dim), int(longest_dim[0][0]))) 
            self.force_orientations = [int(mirror_dim[0][0]), int(leftover_dim), int(longest_dim[0][0])]
            self.force_flips = [1, 1, 1]

            if SP_flip == -1:
                self.downsampled_volume_transposed = self.downsampled_volume_transposed[:, ::-1, :]  # Flip the second axis (A)
                self.force_flips[1] = -1
            if AP_flip == -1:
                self.downsampled_volume_transposed = self.downsampled_volume_transposed[:, :, ::-1]  # Flip the third axis (R)
                self.force_flips[2] = -1
            self.logger.info('If force flips or force orientation is on, this should not be printing right now...')
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
        self.downsampled_volume = normalize_to_255(self.downsampled_volume)

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
        stack_oh = normalize_to_255(stack_oh)
        return stack_oh
    
    def crop_border_noise(self, stack_oh, distance_threshold=10,artificial_padding=5):
        """ Try to eliminate noise at the border of tissue """
        self.logger.info('We are cropping noise on border!')
        padded_stack_oh = np.pad(stack_oh, artificial_padding, mode='constant', constant_values=-1)
        distances_oh = distance_transform_edt(padded_stack_oh != -1)
        cleaned_padded_stack_oh = np.where(distances_oh > distance_threshold, padded_stack_oh, 0)
        cropped_volume = cleaned_padded_stack_oh[artificial_padding:-artificial_padding, 
                                        artificial_padding:-artificial_padding, 
                                        artificial_padding:-artificial_padding]
        slice_views(array1=cropped_volume,output_filename=os.path.join(self.drop_path,"cropped_borderoutput.jpg"))
        return cropped_volume

    def grab_ds_image_medidata(self):
        self.new_z_dim, self.new_x_dim, self.new_y_dim = self.downsampled_volume.shape 

class CellImage():
    def __init__(self, MovingImageObject, CellFile, logger):
        # Save the incoming variables as attributes
        self.MIO = MovingImageObject
        self.cell_file = CellFile
        self.logger = logger

    def __call__(self):
        self.logger.info('Creating the Cell Image')
        self.read_cell_count_file()

        self.logger.info('Determine Cell Image Orientation and Align to moving image')
        self.determine_orientation()
        self.first_transform_orientation()

        self.logger.info('Remove any double counts from cell image based on threshold')
        self.remove_double_counts()

        self.logger.info('Downsample CI to MIO coordinate system')
        self.downsample_cell_count_coordinates()

        self.logger.info('Convert cell counts to aggregate mask image')
        self.downsampled_volume = self.generate_mask_image()

        self.logger.info('Apply force flips and/or orientations from MI')
        self.downsampled_volume = self.second_transform_orientation()

        self.logger.info('Finshed with generating Cell Image')
   
    def read_cell_count_file(self):
        """ Convert cell count files into numpy array attributes for class."""
        # Determine channel name
        if '488' in self.cell_file:
            self.channel_name = '488'
        elif '561' in self.cell_file:
            self.channel_name = '561'
        elif '647' in self.cell_file:
            self.channel_name = '647'
        elif '785' in self.cell_file:
            self.channel_name = '785'
        
        self.logger.info(f'The Channel is {self.channel_name}')

        # Load in counts, arranges axes and eliminate double counts
        self.counts_oh = pd.read_csv(self.cell_file).to_numpy().astype(int)

    def determine_orientation(self):
        """ Compare orientation of MIO and CI to determine how to move CI """
        # Make sure dims match between cell counts and moving image 
        MIO_dims = np.array([self.MIO.orig_z_dim, self.MIO.orig_x_dim, self.MIO.orig_y_dim]).astype(np.int32)
        CI_dims = self.counts_oh.max(axis=0).astype(np.int32)
        sorted_MIO_dims = np.argsort(MIO_dims)[::-1]  # Indices of sorted shape1
        sorted_CI_dims = np.argsort(CI_dims)[::-1]  # Indices of sorted shape2
        self.MIO_CI_axis_map = {sorted_MIO_dims[i]: sorted_CI_dims[i] for i in range(3)}
        self.CI_to_MIO_map = [self.MIO_CI_axis_map[i] for i in range(3)]

    def first_transform_orientation(self):
        """ Perform first transformation mapping CI to MIO original space """
        self.counts_oh =  self.counts_oh [:,[self.CI_to_MIO_map]]
        #self.counts_oh  = self.counts_oh [:,[1,0,2]] # Note 03/23/25 Potentially delete line. 
        self.counts_oh  = np.asarray(self.counts_oh ).squeeze()
   
    def downsample_cell_count_coordinates(self):
        # Get original shape from MIO, this will be the current shape of image
        MIO_old_dims = np.array([self.MIO.orig_z_dim, self.MIO.orig_x_dim, self.MIO.orig_y_dim]).astype(np.int32)
        MIO_new_dims = np.array([self.MIO.new_z_dim, self.MIO.new_x_dim, self.MIO.new_y_dim]).astype(np.int32)
        # Get new shape of MIO, this will be  
        ds_rate = MIO_new_dims/MIO_old_dims
        self.counts_oh = self.counts_oh*ds_rate

    def remove_double_counts(self):
        """ Deletes double counts from dataset 
        Important -- Must be run on coordinates BEFORE they are downsampled
        """
        self.counts_oh = determine_doublecount_points(array1=self.counts_oh, array2=self.counts_oh, threshold=3)

    def generate_mask_image(self):
        """ Convert cell counts into a 3D image """
        self.coordinate_mask = np.zeros((self.MIO.new_z_dim,self.MIO.new_x_dim,self.MIO.new_y_dim), dtype=int)
        max_indices = np.array(self.coordinate_mask.shape) - 1

        for cell in self.counts_oh:
            x, y, z = np.clip(np.round(cell).astype(np.int32), 0, max_indices)
            self.coordinate_mask[x, y, z] += 1
        
        return self.coordinate_mask
            
    def second_transform_orientation(self):
        if self.MIO.force_orientations is not None:
            self.downsampled_volume_transposed = np.transpose(self.downsampled_volume, 
                                                                  (int(self.MIO.force_orientations[0]), 
                                                                   int(self.MIO.force_orientations[1]), 
                                                                   int(self.MIO.force_orientations[2]))) 
        else:
            self.downsampled_volume_transposed = self.downsampled_volume.copy() # Written as a quick fix  03/10/2025

        if self.MIO.force_flips is not None:
            if self.MIO.force_flips[0]==-1:
                self.downsampled_volume_transposed = np.copy(self.downsampled_volume_transposed[::-1, :, :]) # Flip the first axis (Dosral-Ventral)
            if self.MIO.force_flips[1] == -1:
                self.downsampled_volume_transposed = np.copy(self.downsampled_volume_transposed[:, ::-1, :]) # Flip the second axis (Right-Left)
            if self.MIO.force_flips[2] == -1:
                self.downsampled_volume_transposed = np.copy(self.downsampled_volume_transposed[:, :, ::-1])  # Flip the third axis (Anterior-Posterior)
        
        return self.downsampled_volume_transposed
