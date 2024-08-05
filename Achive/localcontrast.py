from PIL import Image
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed

def adjust_contrast(img, alpha=1.5, beta=10):
    """Adjusts the contrast of an image.
    Alpha controls the degree of enhancement, and beta controls the brightness.
    """
    img = img.convert('RGB')
    img = np.array(img)
    img = img.astype(np.float32)
    img = img * alpha + beta
    img[img > 255] = 255
    img = img.astype(np.uint8)
    img = Image.fromarray(img)
    return img

def tile_image(img, tile_size=(64, 64)):
    """Tiles an image into smaller images of the specified size"""
    width, height = img.size
    tiles = []
    for i in range(0, width, tile_size[0]):
        for j in range(0, height, tile_size[1]):
            box = (i, j, i + tile_size[0], j + tile_size[1])
            tile = img.crop(box)
            tiles.append(tile)
    return tiles

# Open the TIFF stack
img = Image.open('path/to/tiffstack.tif')

# Iterate over the frames of the TIFF stack
for i in range(img.n_frames):
    img.seek(i)
    frame = img.copy()
    # Break the image into tiles
    tiles = tile_image(frame, tile_size=(64, 64))

    with ProcessPoolExecutor() as executor:
        # Submit the contrast adjustment tasks to the executor
        futures = [executor.submit(adjust_contrast, tile) for j, tile in enumerate(tiles)]

        # Iterate over the completed tasks and save the results
        for j, future in enumerate(as_completed(futures)):
            tile = future.result()
            tile.save('path/to/enhanced_tile_{}_{}.tif'.format(i, j))

