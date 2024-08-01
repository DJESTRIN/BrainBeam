import tifffile
from concurrent.futures import ThreadPoolExecutor
import argparse
from skimage.util import view_as_windows
import numpy as np
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

import numpy as np
from skimage import io

def tile_image(image_path, tile_size, stride):
    """
    Break a TIFF image into tiles with a specified stride.
    :param image_path: path to the TIFF image
    :param tile_size: size of the tiles (height, width)
    :param stride: stride for tiling (height, width)
    :return: a list of tiles as numpy arrays
    """
    # Load the TIFF image
    image = io.imread(image_path)

    # Get the height and width of the image
    height, width = image.shape[:2]

    # Initialize the list of tiles
    tiles = []

    # Iterate over the rows of the image
    for y in range(0, height - tile_size[0] + 1, stride[0]):
        # Iterate over the columns of the image
        for x in range(0, width - tile_size[1] + 1, stride[1]):
            # Get the current tile
            tile = image[y:y + tile_size[0], x:x + tile_size[1]]
            # Append the tile to the list of tiles
            tiles.append(tile)

    return tiles
import numpy as np

def reconstruct_image(tiles, tile_size, image_size):
    """
    Reconstruct an image from a list of tiles.
    :param tiles: list of tiles as numpy arrays
    :param tile_size: size of the tiles (height, width)
    :param image_size: size of the original image (height, width)
    :return: the reconstructed image as a numpy array
    """
    # Initialize the reconstructed image with zeros
    reconstructed_image = np.zeros(image_size, dtype=tiles[0].dtype)

    # Get the number of rows and columns in the image
    rows, cols = image_size[0] // tile_size[0], image_size[1] // tile_size[1]

    # Iterate over the rows of the image
    for row in range(rows):
        # Iterate over the columns of the image
        for col in range(cols):
            # Get the index of the current tile
            index = row * cols + col
            # Get the current tile
            tile = tiles[index]
            # Paste the current tile into the reconstructed image
            reconstructed_image[row*tile_size[0]:(row+1)*tile_size[0], col*tile_size[1]:(col+1)*tile_size[1]] = tile
    return reconstructed_image

# Define a function to perform local contrast enhancement on a single image
def enhance_image(image, window_size, stride):
    # Create the view of the image as windows
    windows = view_as_windows(image, window_size, stride)

    # Compute the mean and standard deviation of each window
    means = np.mean(windows, axis=(-3, -2))
    stds = np.std(windows, axis=(-3, -2))

    # Perform local contrast enhancement on each window
    contrast_enhanced = (windows - means[..., np.newaxis, np.newaxis]) / stds[..., np.newaxis, np.newaxis]

    # Reconstruct the image from the contrast-enhanced windows
    reconstructed = np.zeros_like(image)
    count = np.zeros_like(image)
    for i in range(0, image.shape[0] - window_size[0], stride):
        for j in range(0, image.shape[1] - window_size[1], stride):
            reconstructed[i:i + window_size[0], j:j + window_size[1]] += contrast_enhanced[i // stride, j // stride]
            count[i:i + window_size[0], j:j + window_size[1]] += 1
    reconstructed /= count
    return reconstructed

if __name__=='__main__':
  # Use argparse to define command-line arguments
  parser = argparse.ArgumentParser(description="Perform local contrast enhancement on a TIFF stack.")
  parser.add_argument("input_directory", type=str, help="The directory containing the input TIFF stack.")
  parser.add_argument("output_directory", type=str, help="The directory to save the output TIFF stack.")
  parser.add_argument("--window_size", type=int, nargs=2, default=(50,50), help="The size of the window for tiling")
  parser.add_argument("--stride", type=int, default=10, help="The stride for tiling")
  args = parser.parse_args()

  # Read in the TIFF stack
  with tifffile.TiffFile(args.input_directory) as tif:
      stack = tif.asarray()

  window_size = tuple(args.window_size)
  stride = args.stride

  # Use a ThreadPoolExecutor to process the images in parallel
  with ThreadPoolExecutor() as executor:
      # Submit the enhance_image function for each image in the stack to the executor
      futures = [executor.submit(enhance_image, image, window_size, stride) for image in stack]

      # Iterate over the completed futures to get the contrast-enhanced images
      contrast_enhanced_images = [future.result() for future in futures]

   # Convert the list
  tifffile.imsave(args.output_directory, contrast_enhanced_images)
