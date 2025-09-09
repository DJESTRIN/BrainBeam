import os
import numpy as np
from tifffile import TiffFile
from joblib import Parallel, delayed
import matplotlib.pyplot as plt
from multiprocessing import cpu_count
from tqdm import tqdm
from tempfile import mkdtemp
import shutil

def extract_ap_slice(input_folder, ap_index, save_path):
    # Get sorted list of TIFF files
    tiff_files = sorted([
        os.path.join(input_folder, f)
        for f in os.listdir(input_folder)
        if f.lower().endswith(('.tif', '.tiff'))
    ])

    if not tiff_files:
        raise FileNotFoundError("No TIFF files found.")

    # Load metadata from first file
    with TiffFile(tiff_files[0]) as tif:
        height, width = tif.pages[0].shape
        dtype = tif.pages[0].dtype

    n_slices = len(tiff_files)

    # Shared memory setup
    temp_folder = mkdtemp()
    shared_array = np.memmap(
        filename=os.path.join(temp_folder, 'ap_slice.dat'),
        dtype=dtype,
        mode='w+',
        shape=(n_slices, width)  # 1 row from each file
    )

    def process_file(i):
        with TiffFile(tiff_files[i]) as tif:
            try:
                row = tif.pages[0].asarray()[ap_index, :]
                shared_array[i, :] = row
            except IndexError:
                print(f"AP index {ap_index} out of bounds in file {tiff_files[i]}")
    
    # Parallel processing
    Parallel(n_jobs=max(cpu_count() - 1, 1))(
        delayed(process_file)(i) for i in tqdm(range(n_slices), desc="Loading slices")
    )

    # Copy out of shared memory
    final_image = np.array(shared_array)

    # Save and plot
    plot_image_exact(final_image, save_path)

    # Cleanup shared memory
    del shared_array
    shutil.rmtree(temp_folder)

    return final_image

def plot_image_exact(image, save_path, cmap='gray'):
    height, width = image.shape

    # figsize in inches = pixels / dpi
    dpi = 100  # or 72, or 96 — just choose your preferred resolution
    figsize = (width / dpi, height / dpi)

    plt.figure(figsize=figsize, dpi=dpi)
    plt.imshow(image, cmap=cmap, interpolation='nearest', aspect='equal')
    plt.axis('off')
    plt.tight_layout(pad=0)
    plt.savefig(save_path, dpi=dpi, bbox_inches='tight', pad_inches=0)
    plt.close()

def load_subvolume(
    folder,
    dv_start, dv_stop,
    ap_start, ap_stop,
    lr_start, lr_stop,
    save_path='max_proj.png'):
    # Collect and sort TIFF files
    tiff_files = sorted([
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith(('.tif', '.tiff'))
    ])
    if not tiff_files:
        raise FileNotFoundError("No TIFF files found.")

    # Validate AP range
    total_slices = len(tiff_files)
    if ap_start < 0 or ap_stop > total_slices or ap_start >= ap_stop:
        raise ValueError(f"Invalid AP slice range: {ap_start} to {ap_stop}")

    # Load shape and dtype from first file
    with TiffFile(tiff_files[0]) as tif:
        full_height, full_width = tif.pages[0].shape
        dtype = tif.pages[0].dtype

    # Validate DV and LR ranges
    if not (0 <= dv_start < dv_stop <= full_height):
        raise ValueError(f"Invalid DV range: {dv_start} to {dv_stop}")
    if not (0 <= lr_start < lr_stop <= full_width):
        raise ValueError(f"Invalid LR range: {lr_start} to {lr_stop}")

    dv_size = dv_stop - dv_start
    lr_size = lr_stop - lr_start
    ap_size = ap_stop - ap_start

    # Create memmap to hold subvolume: shape = (AP, DV, LR)
    temp_dir = mkdtemp()
    memmap_path = os.path.join(temp_dir, 'subvolume.dat')
    subvol = np.memmap(memmap_path, dtype=dtype, mode='w+', shape=(ap_size, dv_size, lr_size))

    def load_one_slice(i):
        file_idx = ap_start + i
        with TiffFile(tiff_files[file_idx]) as tif:
            full_img = tif.pages[0].asarray()
            # Extract requested subregion: rows = DV range, cols = LR range
            return full_img[dv_start:dv_stop, lr_start:lr_stop]

    # Parallel load all slices into memmap
    results = Parallel(n_jobs=max(cpu_count() - 1, 1))(
        delayed(load_one_slice)(i) for i in tqdm(range(ap_size), desc='Loading subvolume')
    )

    for i, slice_2d in enumerate(results):
        subvol[i, :, :] = slice_2d

    # Compute max projection along AP axis (axis=0)
    max_proj = np.max(subvol, axis=0)

    plot_image_exact(image=max_proj,save_path=save_path)

    # Cleanup memmap file and folder
    del subvol
    shutil.rmtree(temp_dir)

    return max_proj

if __name__=='__main__':
    num_workers = max(os.cpu_count() - 1, 1)
    path = r"C:\Users\listo\data\20231016_17_52_28_CAGE4467200_ANIMAL04_VIRUSRABIES_CORTEXPERIMENTAL_SEXFEMALE\Ex_647_Em_680"
    files = [f for f in os.listdir(path) if f.lower().endswith('.tif') or f.lower().endswith('.tiff')]

    if not files:
        raise FileNotFoundError("No TIFF files found in directory.")

    first_file = os.path.join(path, files[0])

    with TiffFile(first_file) as tif:
        img = tif.pages[0].asarray()
        print("File:", first_file)
        print("Shape:", img.shape)
        print("Dtype:", img.dtype)

    image = extract_ap_slice(
    input_folder=path,
    ap_index=7000,  
    save_path='ap_slice_7000.png')

    max_projection = load_subvolume(
    folder=path,
    dv_start=1000, dv_stop=2000,
    ap_start=9000, ap_stop=9500,
    lr_start=3700, lr_stop=7400,
    save_path='max_projection_AP.png')



