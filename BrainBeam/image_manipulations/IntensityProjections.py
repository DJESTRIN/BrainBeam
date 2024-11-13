#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: IntensityProjections.py
Description: 
Author: David Estrin
Date: 2024-11-11
Version: 1.0
"""
import glob, os
import tqdm
import ipdb
from skimage.io import imread
import matplotlib.pyplot as plt
import numpy as np
from multiprocessing import Pool
import pandas as pd
from PIL import Image
import argparse

class IntensityProjection():
    def __init__(self,
                 directory=None,
                 list_of_images=None,
                 image_filetype='tif',
                 recursive_search=True,
                 slice_type='Axial',
                 x_start=None,
                 x_stop=None,
                 y_start=None,
                 y_stop=None,
                 z_start=None,
                 z_stop=None):
        """ IntenstiyProjection class 
        Inputs:
            directory -- A directory containing image files
            list_of_images -- A list of images given instead of a directory
            image_filetype -- A file type to search for (ex .tif)
            recursive_search -- Recurisively search a root directory for images
            slice_type -- The direction output MIP will be in. 
                IMPORTANT: images are assumed to start in axial position along z axis. 
            x_start, xstop, y_start, y_stop, z_start, z_stop -- Where to start and stop images to include in final image

        Outputs:
            objfile
            MIP_array
            MIP_image
        """
        # Get a list of images to run Intensity Projection on
        if list_of_images is None:
            try:
                self.images=glob.glob(directory+f"*.{image_filetype}*",recursive=recursive_search)
            except:
                raise("directory and list_of_images not provided, therefore error")
        else:
            self.images=list_of_images

        # Determine list of images is real
        if not self.images:
            raise('List of images is empty, check search patterns')
        
        # Determine output slice type from options
        if slice_type not in {'Axial', 'Coronal', 'Sagittal'}:
            raise ValueError("Invalid slice_type. Choose from 'Axial', 'Coronal', or 'Sagittal'.")
        self.slice_type = slice_type

        # Set starts and stops
        self.x_start=x_start
        self.x_stop=x_stop
        self.y_start=y_start
        self.y_stop=y_stop
        self.z_start=z_start
        self.z_stop=z_stop

    def __call__(self):
        self.update_positionings()
        self.MIP=self.MaxIntensityProjection()
        return self.MIP

    def update_positionings(self):
        """ Set start and stop values """
        # Get default image parameters
        height,width=np.asarray(imread(self.images[0])).shape
        depth=len(self.images)

        # Update parameters to default if input is None
        if self.x_start is None:
            self.x_start=0
        if self.x_stop is None:
            self.x_stop=height
        if self.y_start is None:
            self.y_start=0
        if self.y_stop is None:
            self.y_stop=width
        if self.z_start is None:
            self.z_start=0
        if self.z_stop is None:
            self.z_stop=depth

    def grab_image(self,image_file):
        """ Grab current image and crop depending on settings.
            Flip image depending on settings """
        # Read image from image_file
        image_oh=np.asarray(imread(image_file))
        image_oh=image_oh[self.x_start:self.x_stop,self.y_start:self.y_stop]
        return image_oh

    def coronal_helper(self,image_file):
        return np.max(self.grab_image(image_file),axis=0)

    def sagittal_helper(self,image_file):
        return np.max(self.grab_image(image_file),axis=1)

    def MaxIntensityProjection(self):
        """ Calculate max intensity projection for series of images, 2 images at a time """
        if self.slice_type=='Axial':
            # Load first image as default max
            image_final=self.grab_image(self.image[0])
            image_final=image_final[...,np.newaxis]

            # Loop over rest of images in stack
            for image in self.images[1:]:
                image_oh=imread(image)
                image_oh=np.array(image_oh)
                image_oh=image_oh[...,np.newaxis]
                precalculation=np.concatenate((image_final,image_oh),axis=2)
                image_final=np.max(precalculation,axis=2)
                image_final=image_final[...,np.newaxis]
        
        if self.slice_type=='Coronal':
            with Pool() as pool:
                coronal_image = []
                for imageoh in tqdm.tqdm(pool.imap(self.coronal_helper, self.images), total=len(self.images)):
                    coronal_image.append(imageoh)
                image_final=np.asarray(coronal_image)

        if self.slice_type=='Sagittal':
            with Pool() as pool:
                sagittal_image = []
                for imageoh in tqdm.tqdm(pool.imap(self.sagittal_helper, self.images), total=len(self.images)):
                    sagittal_image.append(imageoh)
                image_final=np.asarray(sagittal_image)

        return image_final

class IntensityProjectionWithCounts(IntensityProjection):
    def __init__(self,
                 directory=None,
                 list_of_images=None,
                 image_filetype='tif',
                 recursive_search=True,
                 slice_type='Axial',
                 x_start=None,
                 x_stop=None,
                 y_start=None,
                 y_stop=None,
                 z_start=None,
                 z_stop=None, 
                 count_files=[]):
        
        super().__init__(directory,
                         list_of_images,
                         image_filetype,
                         recursive_search,
                         slice_type,
                         x_start,
                         x_stop,
                         y_start,
                         y_stop,
                         z_start,
                         z_stop)
        
        if count_files:
            self.count_files = count_files
            self.cell_counts=[]

            # Loop over files and load in counts
            for file in self.count_files:
                cell_counts_oh = pd.read_csv(file)
                cell_counts_oh = cell_counts_oh.to_numpy()
                self.cell_counts.append(cell_counts_oh)
    
    def find_relevant_counts(self):
        """ Find the relevant counts in the x, y, z ranges """
        # Filter cell counts based on x_start, x_stop, y_start, y_stop, z_start, z_stop
        self.cell_counts_oh=[]
        for countsoh in self.cell_counts:
            new_countsoh = countsoh[(countsoh[:, 0] >= self.x_start) & (countsoh[:, 0] <= self.x_stop) & 
                                        (countsoh[:, 1] >= self.y_start) & (countsoh[:, 1] <= self.y_stop) & 
                                        (countsoh[:, 2] >= self.z_start) & (countsoh[:, 2] <= self.z_stop)]
            self.cell_counts_oh.append(new_countsoh)

    def overlay_counts_on_MIP(self):
        """ Takes Intensity Projection and Adds cell counts """
        
        def coordinate_to_square(mask,coordinate,side_length=3):
            mask[(int(coordinate[0])-side_length):(int(coordinate[0])+side_length),(int(coordinate[1])-side_length):(int(coordinate[1])+side_length)]=1
            return mask
        
        # Loop over current set of counts to generate a mask
        all_masks=[]
        for countsoh in self.cell_counts_oh:
            mask_img=np.zeros((self.MIP.shape))
            if self.slice_type=='Axial':
                masked_coordinates=np.delete(countsoh,2,axis=1)
                for celloh in masked_coordinates:
                    mask_img=coordinate_to_square(mask_img,celloh)

            if self.slice_type=='Coronal':
                masked_coordinates=np.delete(countsoh,0,axis=1)
                for celloh in masked_coordinates:
                    mask_img=coordinate_to_square(mask_img,celloh,side_length=7)

            if self.slice_type=='Sagittal':
                masked_coordinates=np.delete(countsoh,1,axis=1)
                for celloh in masked_coordinates:
                    mask_img=coordinate_to_square(mask_img,celloh)
            
            # Append the mask image to list
            all_masks.append(mask_img)

        return all_masks #return all masks
            
    def __call__(self):
        self.update_positionings()
        self.MIP=self.MaxIntensityProjection()

        # Get relevant cell counts
        self.find_relevant_counts()

        # Generate masks if cells are present
        if self.cell_counts_oh:
            self.masks=self.overlay_counts_on_MIP()
        else:
            print('No cells to include in mask')
            self.masks=np.zeros((self.MIP.shape))

        return self.MIP,self.masks

def divide_list_into_batches(lst, num_batches):
    batch_size = len(lst) // num_batches  # Calculate the base size of each batch
    remainder = len(lst) % num_batches    # Calculate if there's any remainder

    batches = []
    start = 0
    for i in range(num_batches):
        # Distribute the remainder among the first few batches
        end = start + batch_size + (1 if i < remainder else 0)
        batches.append(lst[start:end])
        start = end

    return batches

def create_number_batches(total, num_batches):
    batch_size = total // num_batches
    remainder = total % num_batches
    
    batches = []
    start = 0
    for i in range(num_batches):
        end = start + batch_size + (1 if i < remainder else 0)
        batches.append(list(range(start, end)))
        start = end

    return batches

def adjust_brightness_contrast_np(image_array, brightness_factor, contrast_factor):
    # Ensure the image is in the range 0-255 (assuming the image is uint8)
    image_array = np.clip(image_array, 0, 255)
    
    # Convert to float for safe calculations (if it's uint8)
    img_float = image_array.astype(np.float32)
    
    # Adjust contrast: Contrast factor greater than 1 increases contrast, between 0 and 1 decreases
    mean = np.mean(img_float, axis=(0, 1), keepdims=True)  # Mean of image for center of contrast
    img_contrast = (img_float - mean) * contrast_factor + mean
    
    # Adjust brightness: Brightness factor greater than 1 increases brightness
    img_bright_contrast = img_contrast * brightness_factor
    
    # Clip values to stay in the valid range [0, 255] and convert back to uint8
    img_bright_contrast = np.clip(img_bright_contrast, 0, 255).astype(np.uint8)
    
    return img_bright_contrast

def generate_MIP_grid(diroh,cellcountfile,slice_type='Coronal',rows=5,cols=5,filetype='tif'):
    """ Create a m x n grid of MIP images """
    images_oh = glob.glob(os.path.join(diroh,f'*.{filetype}*')) #Find all images in a given directory
    grids=rows*cols

    # Create empty lists to place final data into
    MIP_grid=[]
    Mask_grid=[]

    if slice_type=='Axial':
        batches = divide_list_into_batches(images_oh, grids)
        for batchoh in batches:
            MIPobj=IntensityProjectionWithCounts(list_of_images=images_oh,
                                                 slice_type=slice_type,
                                                 z_start=batchoh[0],
                                                 z_stop=batchoh[-1],
                                                 count_files=[cellcountfile]) # Create object
            MIP,Mask=MIPobj() # Run protocol and get MIP for batch of images
            normMIP=(MIP-MIP.min())/(MIP.max()-MIP.min())*255
            fin_MIP = adjust_brightness_contrast_np(normMIP, 5, 2.0)
            MIP_grid.append(fin_MIP)
            Mask_grid.append(Mask)

    else:
        example_image=np.asarray(imread(images_oh[0]))
        height, width=example_image.shape
        if slice_type=='Coronal':
            batches = create_number_batches(height, grids)
            for batchoh in batches:
                MIPobj=IntensityProjectionWithCounts(directory=None,
                                                     list_of_images=images_oh,
                                                     slice_type=slice_type,
                                                     x_start=batchoh[0],
                                                     x_stop=batchoh[1],
                                                     count_files=[cellcountfile]) # Create object
                MIP,Mask=MIPobj() # Run protocol and get MIP for batch of images
                normMIP=(MIP-MIP.min())/(MIP.max()-MIP.min())*255
                fin_MIP = adjust_brightness_contrast_np(normMIP, 5, 2.0)
                MIP_grid.append(fin_MIP)
                Mask_grid.append(Mask)

        if slice_type=='Sagittal':
            batches = create_number_batches(width, grids)
            for batchoh in batches:
                MIPobj=IntensityProjectionWithCounts(directory=None,
                                                     list_of_images=images_oh,
                                                     slice_type=slice_type,
                                                     y_start=batchoh[0],
                                                     y_stop=batchoh[1],
                                                     count_files=[cellcountfile]) # Create object
                MIP,Mask=MIPobj() # Run protocol and get MIP for batch of images
                normMIP=(MIP-MIP.min())/(MIP.max()-MIP.min())*255
                fin_MIP = adjust_brightness_contrast_np(normMIP, 5, 2.0)
                MIP_grid.append(fin_MIP)
                Mask_grid.append(Mask)

    return MIP_grid, Mask_grid

def plot_image_grid(images,output_file,masks=None,rows=5,cols=5):
    col_counter=0
    all_rows=[]
    for image in images:
        if col_counter==0:
            col_oh = image
            col_counter+=1
        else:
            col_oh = np.concatenate((col_oh, image), axis=1)
            col_counter+=1
        
        if col_counter>cols:
            col_counter=0
            all_rows.append(col_oh)

    all_rows=np.asarray(all_rows)
    bigMIP=np.concatenate(all_rows, axis=0)

    if masks is not None:
        col_counter=0
        all_rows=[]
        for mask in masks:
            mask=mask[0]

            if col_counter==0:
                col_oh = image
                col_counter+=1

            else:
                col_oh = np.concatenate((col_oh, mask), axis=1)
                col_counter+=1
            
            if col_counter>=cols:
                col_counter=0
                all_rows.append(col_oh)
    
    all_rows=np.asarray(all_rows)
    bigMask=np.concatenate(all_rows, axis=0)

    save_image_with_mask_to_pdf(image_array=bigMIP,mask_array=bigMask,pdf_path=output_file)

def save_image_with_mask_to_pdf(image_array, mask_array, pdf_path):
    ipdb.set_trace()
    # Convert the grayscale image to a Pillow Image
    grayscale_image = Image.fromarray(image_array).convert("L")
    
    # Convert mask to red overlay
    mask_rgb = Image.fromarray((mask_array * 255).astype(np.uint8)).convert("L")  # Mask as grayscale
    mask_red = Image.new("RGB", mask_rgb.size, (255, 0, 0))  # Red color layer
    mask_overlay = Image.composite(mask_red, Image.new("RGB", mask_rgb.size), mask_rgb)
    
    # Merge grayscale image with red mask overlay
    grayscale_rgb = grayscale_image.convert("RGB")  # Convert grayscale to RGB for color merge
    combined_image = Image.blend(grayscale_rgb, mask_overlay, alpha=0.5)  # Blend with transparency

    # Save to PDF
    combined_image.save(pdf_path, "PDF")


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--image_directory',type=str)
    parser.add_argument('--cell_count_file',type=str)
    args=parser.parse_args()
    # diroh=r'C:\Users\listo\data\20231010_19_26_11_CAGE4467197_ANIMAL02_VIRUSRABIES_CORTEXPERIMENTAL_SEXMALE\Ex_647_Em_680'
    # cellcountfile=r'C:\Users\listo\data\20231010_19_26_11_CAGE4467197_ANIMAL02_VIRUSRABIES_CORTEXPERIMENTAL_SEXMALE\cell_counts.csv'
    allMIPs,allMasks=generate_MIP_grid(args.image_directory,args.cell_count_file,slice_type='Sagittal')
    plot_image_grid(images=allMIPs,
                    output_file=r'C:\Users\listo\data\20231010_19_26_11_CAGE4467197_ANIMAL02_VIRUSRABIES_CORTEXPERIMENTAL_SEXMALE\Ex_647_Em_680MIP.pdf',
                    masks=allMasks)
