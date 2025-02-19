#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: graphics.py
Description: 
Author: David Estrin
Date: 2024-008-15
Version: 1.0
"""

# Load dependencies
import numpy as np
import matplotlib
#matplotlib.use('Agg')
import matplotlib.pyplot as plt
from skimage import measure
from scipy import ndimage
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from scipy.ndimage import zoom
from skimage.filters import threshold_otsu
from PIL import Image
from io import BytesIO
import tqdm
import trimesh
from matplotlib.colors import Normalize
from scipy import stats
import ipdb
import tifffile as tiff
import pandas as pd

# Custom functions and classes
def adjust_image(image, contrast=1.0, brightness=0):
    image = image * contrast
    image = image + brightness
    image = np.clip(image, 0, 255)
    return image

def slice_views(array1, output_filename, array2=None, contrast=None, brightness=None, image_type='max', overlay=False):
    # contrast and brightness must both be numbers
    if contrast is not None and brightness is not None:
        assert isinstance(contrast, (int, float)), "Contrast must be an int or float"
        assert isinstance(brightness, (int, float)), "Brightness must be an int or float"
        adjust = True
    else:
        adjust = False

    num_arrays = 2 if array2 is not None else 1
    num_columns = num_arrays + (1 if overlay and array2 is not None else 0)

    fig, axs = plt.subplots(3, num_columns, figsize=(5 * num_columns, 15))

    for i in range(3):
        for j, array in enumerate([array1, array2] if array2 is not None else [array1]):
            if image_type == 'max':
                projection = array.max(axis=i)
            elif image_type == 'mean':
                projection = array.mean(axis=i)
            elif image_type == 'median':
                projection = np.median(array, axis=i)
            elif image_type == 'std':
                projection = np.std(array, axis=i)
            else:
                raise ValueError("Image type must be either 'max', 'mean', 'median' or 'std'")

            # Adjust brightness and contrast
            if adjust:
                projection = adjust_image(projection, contrast=contrast, brightness=brightness)

            ax = axs[i, j] if num_columns > 1 else axs[i]
            ax.imshow(projection, aspect='equal', cmap='gray', vmin=np.min(projection), vmax=np.max(projection))
            ax.axis('off')

        # Overlay column
        if overlay and array2 is not None:
            if image_type == 'max':
                projection1 = array1.max(axis=i)
                projection2 = array2.max(axis=i)
            elif image_type == 'mean':
                projection1 = array1.mean(axis=i)
                projection2 = array2.mean(axis=i)
            elif image_type == 'median':
                projection1 = np.median(array1, axis=i)
                projection2 = np.median(array2, axis=i)
            elif image_type == 'std':
                projection1 = np.std(array1, axis=i)
                projection2 = np.std(array2, axis=i)

            # Adjust brightness and contrast for overlays
            if adjust:
                projection1 = adjust_image(projection1, contrast=contrast, brightness=brightness)
                projection2 = adjust_image(projection2, contrast=contrast, brightness=brightness)

            # Create RGB overlay
            overlay_image = np.zeros((*projection1.shape, 3), dtype=np.float32)
            overlay_image[..., 0] = projection1 / np.max(projection1) if np.max(projection1) > 0 else 0  # Red channel
            overlay_image[..., 1] = projection2 / np.max(projection2) if np.max(projection2) > 0 else 0  # Green channel

            ax = axs[i, -1]
            ax.imshow(overlay_image, aspect='equal')
            ax.axis('off')

    plt.tight_layout()
    plt.savefig(output_filename)

def overlay_masks(atlas, image, mask, output_filename, num_slices=9, grid_shape=(3,3), atlas_categorical=True):
    
    assert atlas.shape == image.shape == mask.shape, "All inputs must have the same shape."

    # Set atlas values to blue color range
    if atlas_categorical:
        unique_keys = np.unique(atlas.astype(int))
        key_to_color = {}
        for key in unique_keys:
            if key==0:
                key_to_color[key] = 0
            else:
                blue_value = np.random.rand()
                key_to_color[key] = [blue_value]

    # Get evenly spaced slice indices
    depth = atlas.shape[0]
    slice_indices = np.linspace(0, depth - 1, num_slices, dtype=int)

    # Generate figure
    fig, axes = plt.subplots(grid_shape[0], grid_shape[1], figsize=(12, 12))
    axes = axes.ravel()

    # Loop over slices
    for i, (idx1,idx2) in enumerate(zip(slice_indices[:-1],slice_indices[1:])):
        # get intensity projections
        if atlas_categorical:
            atlas_mip = atlas[idx2].astype(int)
            atlas_mip_copy = atlas_mip.copy().astype(np.float32)
            for key, color in key_to_color.items():
                xoh,yoh = np.where(atlas_mip == key)
                if xoh.size>0:
                    atlas_mip_copy[xoh, yoh] = color

        else:
            atlas_mip = np.max(atlas[idx1:idx2], axis=0)
            atlas_mip = atlas_mip/mask.max()

        image_mip = np.max(image[idx1:idx2], axis=0)
        mask_mip = np.max(mask[idx1:idx2], axis=0)
        mask_cell_coordinates = np.where(mask_mip>0)

        # Normalize to 0 to 1 rang

        combined_image = np.zeros(shape=(image_mip.shape[0],image_mip.shape[1],3))
        #image_mip = np.clip(image_mip * 0.1, 0, 1)
        #atlas_mip = np.clip(atlas_mip * 0.5, 0, 1)

        #combined_image [:,:,1] = image_mip
        combined_image [:,:,2] = atlas_mip
        

        # Display in grid
        axes[i].imshow(atlas_mip_copy,cmap="Blues")
        if mask_mip.max()>0:
            axes[i].scatter(x=mask_cell_coordinates[1],y=mask_cell_coordinates[0],color='red',marker='o',s=3,alpha=0.6)
        axes[i].axis("off")
        axes[i].set_title(f"Slices {idx1} to {idx2}")

    plt.tight_layout()
    plt.savefig(output_filename)

class volume_graphics:
    """ Generates 2D and 3D graphics for documenting registration. 
     These graphs include:
      (1) 3D volume images
      (2) 3D volume gifs
      (3) 2D slice images
      (4) 2D slice gifs """
    
    def __init__(self, shots = 10, angles=None):
        self.gifs={}
        self.angles = angles
        self.shots = shots 

    def spin_volume(self,volume1,volume2,label,output):
        self.initiate_gif(label=label)

        for angle in tqdm.tqdm(range(0, 360, self.shots)):
            self.angles=[0,angle]
            self.build_gif(volume1=volume1,volume2=volume2,label=label)
        
        self.save_current_gif(label=label,output_filename=output)

    def initiate_gif(self,label):
        self.gifs[label]=[]

    def add_image_to_gif(self, image, label):
        listoh = self.gifs[label]
        listoh.append(image)
        self.gifs[label] = listoh

    def build_gif(self,volume1,volume2, label):
        current_image = self.plot_surface(volume1=volume1,volume2=volume2)
        self.add_image_to_gif(image=current_image,label=label)

    def save_current_gif(self,label,output_filename):
        listoh = self.gifs[label]
        frames = []

        for imageoh in tqdm.tqdm(listoh):
            imageoh = np.asarray(imageoh)
            fig, ax = plt.subplots()
            ax.imshow(imageoh)
            ax.axis("off")
            fig.canvas.draw()
            image = Image.frombytes('RGB', fig.canvas.get_width_height(),fig.canvas.tostring_rgb())
            frames.append(image)
            plt.close(fig)

        frames[0].save(output_filename, save_all=True, append_images=frames[1:], duration=100, loop=0)

    def extract_surface(self, volume):
        # Thresholding to create a binary mask
        threshold_value = threshold_otsu(volume.ravel())
        binary_mask = volume > threshold_value

        # Largest connected component filtering
        labeled_volume, num_features = ndimage.label(binary_mask)
        sizes = ndimage.sum(binary_mask, labeled_volume, range(num_features + 1))
        largest_label = sizes.argmax() # +1 because labels start from 1
        largest_component = labeled_volume == largest_label # +1 because labels start from 1
        non_zero_indices = np.nonzero(largest_component.astype(np.uint16)) # get non zero values

        # find bounding box info and crop largest component
        start_x, start_y, start_z = np.min(non_zero_indices[0]), np.min(non_zero_indices[1]), np.min(non_zero_indices[2]) # get offset
        end_x, end_y, end_z = np.max(non_zero_indices[0]), np.max(non_zero_indices[1]), np.max(non_zero_indices[2])
        cropped_volume = largest_component[start_x:end_x+1, start_y:end_y+1, start_z:end_z+1]

        # Marching cubes
        verts, faces, _, _ = measure.marching_cubes(cropped_volume, level=0)
        pre_offset = np.array([start_x, start_y, start_z])
        post_offset = np.array([end_x, end_y, end_z])
        return verts, faces, pre_offset, post_offset

    def get_binary_mask(self, verts, faces, start_shape, final_shape, pre_offset, post_offset):
        # Convert verts and faces to binary mask
        mesh = trimesh.Trimesh(vertices=verts, faces=faces)
        voxel_grid = mesh.voxelized(pitch=1.0)  
        binary_mask = voxel_grid.fill()
        binary_mask = binary_mask.matrix.astype(np.uint16)
        binary_mask_filled = np.zeros(start_shape)
        binary_mask_filled[pre_offset[0]:(post_offset[0]+1), pre_offset[1]:(post_offset[1]+1), pre_offset[2]:(post_offset[2]+1)] = binary_mask

        #Upsample binary mask to original shape
        scaling_factors = [final_shape[i] / binary_mask_filled.shape[i] for i in range(len(final_shape))]
        upsampled_binary_mask_filled = zoom(binary_mask_filled, scaling_factors, order=0)
        upsampled_binary_mask_filled = np.round(upsampled_binary_mask_filled).astype(np.uint16)
        return upsampled_binary_mask_filled

    def plot_surface(self, volume1, volume2, downsample_factor = 0.25, pull_binary_mask=False):
        # Downsample the volume by a factor of 2 in each dimension
        downsampled_volume1 = zoom(volume1.astype(np.float32), zoom=downsample_factor, order=1)
        verts1, faces1, pre1, post1 = self.extract_surface(downsampled_volume1)

        downsampled_volume2 = zoom(volume2.astype(np.float32), zoom=downsample_factor, order=1)
        verts2, faces2, pre2, post2 = self.extract_surface(downsampled_volume2)

        if pull_binary_mask:
            self.binary_mask1 = self.get_binary_mask(verts = verts1, faces = faces1, start_shape = downsampled_volume1.shape, final_shape=volume1.shape, 
                                                    pre_offset=pre1, post_offset=post1)
            
            self.binary_mask2 = self.get_binary_mask(verts = verts2, faces = faces2, start_shape = downsampled_volume2.shape, final_shape=volume2.shape, 
                                                    pre_offset=pre2, post_offset=post2)
            
            return self.binary_mask1, self.binary_mask2
        
        # Visualization of the surface mesh
        fig = plt.figure(figsize=(20, 10))  # Adjust size to accommodate all subplots
        ax1 = fig.add_subplot(131, projection='3d')  # Subplot in the first column
        ax1.add_collection3d(Poly3DCollection(verts1[faces1], alpha=0.05, edgecolor='b'))
        ax1.add_collection3d(Poly3DCollection(verts2[faces2], alpha=0.05, edgecolor='g'))
        pad = 50  # Padding value to add around the object
        ax1.set_xlim(0 - pad, downsampled_volume1.shape[0] + pad)
        ax1.set_ylim(0 - pad, downsampled_volume1.shape[1] + pad)
        ax1.set_zlim(0 - pad, downsampled_volume1.shape[2] + pad)
        if self.angles is not None:
            elevoh, azimoh = self.angles
            ax1.view_init(elev=elevoh, azim=azimoh)
        ax1.axis("off")
        ax1.set_title("3D Subplot 1")

        # Second subplot
        ax2 = fig.add_subplot(132, projection='3d')  
        ax2.add_collection3d(Poly3DCollection(verts1[faces1], alpha=0.05, edgecolor='b'))  
        ax2.set_xlim(0 - pad, downsampled_volume1.shape[0] + pad)
        ax2.set_ylim(0 - pad, downsampled_volume1.shape[1] + pad)
        ax2.set_zlim(0 - pad, downsampled_volume1.shape[2] + pad)
        if self.angles is not None:
            elevoh, azimoh = self.angles
            ax2.view_init(elev=elevoh, azim=azimoh)
        ax2.axis("off")
        ax2.set_title("3D Subplot 2")

        # Third subplot
        ax3 = fig.add_subplot(133, projection='3d')  
        ax3.add_collection3d(Poly3DCollection(verts2[faces2], alpha=0.05, edgecolor='g'))  
        ax3.set_xlim(0 - pad, downsampled_volume1.shape[0] + pad)
        ax3.set_ylim(0 - pad, downsampled_volume1.shape[1] + pad)
        ax3.set_zlim(0 - pad, downsampled_volume1.shape[2] + pad)
        if self.angles is not None:
            elevoh, azimoh = self.angles
            ax3.view_init(elev=elevoh, azim=azimoh)
        ax3.axis("off")
        ax3.set_title("3D Subplot 3")

        # Show the figure
        plt.tight_layout()
        
        buf = BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight')  # Render to a buffer as PNG
        buf.seek(0)  # Rewind the buffer to the beginning

        # Convert the image to a NumPy array
        image = np.array(Image.open(buf))

        # Close the buffer and figure
        buf.close()
        plt.close(fig)

        return image


def quick_cell_plot(ds_image_file,cell_counts_file):
    """ Generate a fast plot of cell coordinates over the downsampled image volume """
    scalings = [50/2,50/2.3,50/2.3]
    downsampled_volume = tiff.imread(ds_image_file)
    cell_counts = pd.read_csv(cell_counts_file).to_numpy()
    cell_counts_ds = cell_counts.copy()
    for i in range(len(cell_counts.T)):
        cell_counts_ds[:,i] = cell_counts_ds[:,i]/scalings[i]

    cell_counts_ds = np.round(cell_counts_ds).astype(int)

    # Generate a gif 
    gif_frames = []
    for i in tqdm.tqdm(range(len(downsampled_volume))):
        fig, ax = plt.subplots()
        ax.imshow(downsampled_volume[i], cmap='Greens',vmin=downsampled_volume.min(),vmax=(downsampled_volume.max()/15))  # Plot the image in green
        
        mask = cell_counts_ds[:, 2] == i
        coords_in_slice = cell_counts_ds[mask]
        if len(coords_in_slice) > 0:
            ax.scatter(coords_in_slice[:, 0], coords_in_slice[:, 1], color='red', marker='o',s=3,alpha=0.3)

        ax.axis("off")
        fig.canvas.draw()
        image = Image.frombytes('RGB', fig.canvas.get_width_height(),fig.canvas.tostring_rgb())
        gif_frames.append(image)
        plt.close(fig)

    gif_frames[0].save('c197_a02.gif', save_all=True, append_images=gif_frames[1:], duration=50, loop=0)

if __name__=='__main__':
    imageoh = r'C:\Users\listo\example_registration_data\sub1_output\current_run_2025_01_21_20_54_54\downsampled_moving_image.tiff'
    cell_count_file = r'C:\Users\listo\example_registration_data\sub1_output\current_run_2025_01_21_20_54_54\c197_a02_cell_counts.csv'
    quick_cell_plot(ds_image_file=imageoh,cell_counts_file=cell_count_file)