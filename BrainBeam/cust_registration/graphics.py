import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import ipdb
import os

def volume_scatter_plot(brain_volume, drop_path, volume2=None, label='Atlas'):
    if volume2 is None:
        thresh = np.percentile(brain_volume,65)
        coords = np.argwhere(brain_volume > thresh)  
        x, y, z = coords[:, 0], coords[:, 1], coords[:, 2]
        intensity = brain_volume[x, y, z]  # Can be replaced with other measures
        downsample_fraction = 0.1  # Keep 10% of the points

        num_points = len(x)
        num_samples = int(num_points * downsample_fraction)
        print(num_samples)
        selected_indices = np.random.choice(num_points, num_samples, replace=False)

        x_down = x[selected_indices]
        y_down = y[selected_indices]
        z_down = z[selected_indices]
        intensity_down = intensity[selected_indices]

        fig = plt.figure(figsize=(8, 8))
        ax = fig.add_subplot(111, projection='3d')

        ax.scatter(z_down, x_down, -y_down, c=intensity_down, cmap='jet', s=1, alpha=0.7)
        ax.grid(False)  
        ax.set_axis_off()      
        ax.set_xticks([]) 
        ax.set_yticks([]) 
        ax.set_zticks([])  
        ax.set_title(label, pad=20)
    
    else:
        thresh = np.percentile(brain_volume,65)
        coords = np.argwhere(brain_volume > thresh)  
        x, y, z = coords[:, 0], coords[:, 1], coords[:, 2]
        intensity = brain_volume[x, y, z]  # Can be replaced with other measures
        downsample_fraction = 0.1  # Keep 10% of the points

        num_points = len(x)
        num_samples = int(num_points * downsample_fraction)
        print(num_samples)
        selected_indices = np.random.choice(num_points, num_samples, replace=False)

        x_down = x[selected_indices]
        y_down = y[selected_indices]
        z_down = z[selected_indices]
        intensity_down = intensity[selected_indices]

        thresh = np.percentile(volume2,65)
        coords = np.argwhere(volume2 > thresh)  
        x, y, z = coords[:, 0], coords[:, 1], coords[:, 2]
        intensity = volume2[x, y, z]  # Can be replaced with other measures
        downsample_fraction = 0.1  # Keep 10% of the points

        num_points = len(x)
        num_samples = int(num_points * downsample_fraction)
        print(num_samples)
        selected_indices = np.random.choice(num_points, num_samples, replace=False)

        x_down2 = x[selected_indices]
        y_down2 = y[selected_indices]
        z_down2 = z[selected_indices]
        intensity_down2 = intensity[selected_indices]


        fig = plt.figure(figsize=(8, 8))
        ax = fig.add_subplot(111, projection='3d')

        ax.scatter(z_down, x_down, -y_down, c=intensity_down, cmap='jet', s=1, alpha=0.7)
        ax.scatter(z_down2, x_down2, -y_down2, c=intensity_down2, cmap='Greens', s=1, alpha=0.7)
        ax.grid(False)  
        ax.set_axis_off()      
        ax.set_xticks([]) 
        ax.set_yticks([]) 
        ax.set_zticks([])  
        ax.set_title(label, pad=20)
    
    plt.savefig(os.path.join(drop_path,f'{label}.jpg'))