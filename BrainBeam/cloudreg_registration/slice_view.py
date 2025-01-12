import numpy as np
import matplotlib.pyplot as plt

def slice_view(x, y, z, I, n=5, clim=None):
    # Set default values for missing arguments
    if isinstance(x, np.ndarray):  # x is I, and we need to set defaults for x, y, z
        I = x
        x = np.arange(I.shape[1])
        y = np.arange(I.shape[0])
        z = np.arange(I.shape[2])
    
    if len(I.shape) == 3 or I.shape[3] == 1:
        nx = [I.shape[1], I.shape[0], I.shape[2]]
        
        if clim is None:
            qlim = [0.01, 0.99]
            clim = np.percentile(I, qlim)
            if clim[1] <= clim[0]:
                clim[1] = clim[0] + 1
        
        # Last index fixed
        slices = np.linspace(1, nx[2], n + 2)[1:-1].astype(int)
        fig, axs = plt.subplots(3, n, figsize=(15, 10))
        for i, s in enumerate(slices):
            ax = axs[0, i]
            ax.imshow(I[:, :, s], aspect='auto', cmap='gray', vmin=clim[0], vmax=clim[1])
            ax.axis('off')

        # Second last index fixed
        slices = np.linspace(1, nx[0], n + 2)[1:-1].astype(int)
        for i, s in enumerate(slices):
            ax = axs[1, i]
            ax.imshow(I[:, s, :], aspect='auto', cmap='gray', vmin=clim[0], vmax=clim[1])
            ax.axis('off')

        # First index fixed
        slices = np.linspace(1, nx[1], n + 2)[1:-1].astype(int)
        for i, s in enumerate(slices):
            ax = axs[2, i]
            ax.imshow(I[s, :, :], aspect='auto', cmap='gray', vmin=clim[0], vmax=clim[1])
            ax.axis('off')

    # Color case
    if len(I.shape) == 4:
        nx = [I.shape[1], I.shape[0], I.shape[2]]
        if clim is None:
            clim = np.percentile(I, [0.01, 0.99])

        if I.shape[3] == 2:
            I = np.concatenate((I, np.zeros((nx[1], nx[0], nx[2]))[:, :, np.newaxis]), axis=3)
        elif I.shape[3] > 3:
            I = I[:, :, :, :3]

        I = (I - clim[0]) / (clim[1] - clim[0])

        # Last index fixed
        slices = np.linspace(1, nx[2], n + 2)[1:-1].astype(int)
        fig, axs = plt.subplots(3, n, figsize=(15, 10))
        for i, s in enumerate(slices):
            ax = axs[0, i]
            ax.imshow(I[:, :, s, :], aspect='auto')
            ax.axis('off')

        # Second last index fixed
        slices = np.linspace(1, nx[0], n + 2)[1:-1].astype(int)
        for i, s in enumerate(slices):
            ax = axs[1, i]
            ax.imshow(I[:, s, :, :], aspect='auto')
            ax.axis('off')

        # First index fixed
        slices = np.linspace(1, nx[1], n + 2)[1:-1].astype(int)
        for i, s in enumerate(slices):
            ax = axs[2, i]
            ax.imshow(I[s, :, :, :], aspect='auto')
            ax.axis('off')

    plt.show()

# Example of usage:
I = np.random.rand(100, 100, 50)  # Example data
slice_view(None, None, None, I)  # You can provide custom x, y, z if necessary
