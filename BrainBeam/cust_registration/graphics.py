import numpy as np
import matplotlib
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

class volume_graphics:
    """ Generates 2D and 3D graphics for documenting registration. 
     These graphs include:
      (1) 3D volume images
      (2) 3D volume gifs
      (3) 2D slice images
      (4) 2D slice gifs """
    
    def __init__(self, angles=None):
        self.gifs={}
        self.angles = angles

    def spin_volume(self,volume1,volume2,label,output):
        self.initiate_gif(label=label)

        for angle in tqdm.tqdm(range(0, 360, 10)):
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
        # Step 1: Thresholding to create a binary mask
        threshold_value = threshold_otsu(volume.ravel())
        binary_mask = volume > threshold_value

        # Step 2: Largest connected component filtering
        labeled_volume, num_features = ndimage.label(binary_mask)
        sizes = ndimage.sum(binary_mask, labeled_volume, range(num_features + 1))
        largest_label = sizes.argmax() # +1 because labels start from 1
        largest_component = labeled_volume == largest_label # +1 because labels start from 1

        # Step 3: Surface extraction using marching cubes
        verts, faces, _, _ = measure.marching_cubes(largest_component, level=0)
        
        return verts, faces

    def plot_surface(self, volume1, volume2, downsample_factor = 0.25):
        # Downsample the volume by a factor of 2 in each dimension

        downsampled_volume1 = zoom(volume1, zoom=downsample_factor, order=1)
        verts1, faces1 = self.extract_surface(downsampled_volume1)

        downsampled_volume2 = zoom(volume2, zoom=downsample_factor, order=1)
        verts2, faces2 = self.extract_surface(downsampled_volume2)

        # Visualization of the surface mesh
        fig = plt.figure(figsize=(10, 10))
        ax = fig.add_subplot(111, projection='3d')
        ax.add_collection3d(Poly3DCollection(verts1[faces1], alpha=0.05, edgecolor='b'))
        ax.add_collection3d(Poly3DCollection(verts2[faces2], alpha=0.05, edgecolor='g'))
        pad = 50  # Padding value to add around the object
        ax.set_xlim(0 - pad, downsampled_volume1.shape[0] + pad)
        ax.set_ylim(0 - pad, downsampled_volume1.shape[1] + pad)
        ax.set_zlim(0 - pad, downsampled_volume1.shape[2] + pad)
        if self.angles is not None:
            elevoh,azimoh = self.angles
            ax.view_init(elev=elevoh, azim=azimoh)
        ax.axis("off")
        
        buf = BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight')  # Render to a buffer as PNG
        buf.seek(0)  # Rewind the buffer to the beginning

        # Convert the image to a NumPy array
        image = np.array(Image.open(buf))

        # Close the buffer and figure
        buf.close()
        plt.close(fig)

        return image

