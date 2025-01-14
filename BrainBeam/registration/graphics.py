import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
from skimage import measure, morphology
from scipy import ndimage
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import os
from scipy.ndimage import zoom
from skimage.filters import threshold_otsu
from PIL import Image
from io import BytesIO
import tqdm
from scipy.ndimage import binary_fill_holes
import trimesh
import ipdb

def adjust_image(image, contrast=1.0, brightness=0):
    image = image * contrast
    image = image + brightness
    image = np.clip(image, 0, 255)
    return image

def slice_views(array1, output_filename, array2=None, contrast=None, brightness=None, image_type='max'):
    # contrast and brightness must both be numbers
    if contrast is not None and brightness is not None:
        assert isinstance(contrast, (int, float)), "Contrast must be an int or float"
        assert isinstance(brightness, (int, float)), "Brightness must be an int or float"
        adjust = True
    else:
        adjust = False

    num_arrays = 2 if array2 is not None else 1
    fig, axs = plt.subplots(3, num_arrays, figsize=(15 * num_arrays, 5))

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

            ax = axs[i, j] if num_arrays == 2 else axs[i]
            ax.imshow(projection, aspect='equal', cmap='gray', vmin=np.min(projection), vmax=np.max(projection))
            ax.axis('off')

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

