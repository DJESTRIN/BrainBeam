#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhance each image by applying a local z-score based on smaller windows with stride.
Converts z-score back to 0-> 255 range

The purpose of this script is to locally apply a contrast. 
The goal would be for one to easily be able to visualize cell bodies and corresponding axons in distal regions. 
"""

from concurrent.futures import ThreadPoolExecutor
import argparse
from skimage.util import view_as_windows
import numpy as np
import glob
from skimage.io import imread, imsave, imshow
import ipdb
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed
from skimage import io

def closestNumber(n, m) :
    # Find the quotient
    q = int(n / m)
     
    # 1st possible closest number
    n1 = m * q
     
    # 2nd possible closest number
    if((n * m) > 0) :
        n2 = (m * (q + 1))
    else :
        n2 = (m * (q - 1))
     
    # if true, then n1 is the required closest number
    if (abs(n - n1) < abs(n - n2)) :
        if n1<n:
            n1=n1+m
        return n1
     
    # else n2 is the required closest number
    if n2<n:
        n2=n2+m
    return n2

def normalize_local(img):
    """Adjusts the contrast of an image.
    Alpha controls the degree of enhancement, and beta controls the brightness.
    """
    img = np.array(img)
    
    #Normalize image
    average=img.mean()
    std=img.std()
    normalized_image=(img-average)/std
    
    #Convert Image back to 0->255 gray scale
    local_min,local_max=normalized_image.min(),normalized_image.max()
    changed_scale=(normalized_image-local_min)/(local_max-local_min)
    grayscale=changed_scale*255
    
    img = grayscale.astype(np.float32)
    img = img.astype(np.uint16)
    return img

def adjust_contrast(img, alpha=1, beta=0):
    """Adjusts the contrast of an image.
    Alpha controls the degree of enhancement, and beta controls the brightness.
    """
    img = np.array(img)
    img = img.astype(np.float32)
    img = img * alpha + beta
    img[img > 255] = 255
    img = img.astype(np.uint16)
    return img


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

    return tiles,(height,width), image

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
def enhance_image(image_path, output_image, tile_size, stride,a,b):
    #Tile image
    tiles, image_size, image=tile_image(image_path,tile_size,stride)
    
    # Perform a contrast adjustment on each tile
    tiles_adjusted=[]
    for i,tile in enumerate(tiles):
        tiles_adjusted.append(adjust_contrast(tile,alpha=a,beta=b))
    ipdb.set_trace()
        
    #Put adjusted tiles back into a singl image
    updated_image=reconstruct_image(tiles_adjusted, tile_size, image_size)
    
    #Save the image
    
    
    #display the image
    plt.figure()
    imshow(adjust_contrast(image,alpha=1,beta=30),cmap='gray')
    plt.show()
    
    plt.figure()
    imshow(adjust_contrast(updated_image,alpha=1,beta=30),cmap='gray')
    plt.show()
    
    return image, updated_image

__name__=='__main__'
if __name__=='__main__':
  # Use argparse to define command-line arguments
  parser = argparse.ArgumentParser(description="Perform local contrast enhancement on a TIFF stack.")
  parser.add_argument("--input_directory", type=str, help="The directory containing the input TIFF stack.")
  parser.add_argument("--output_directory", type=str, help="The directory to save the output TIFF stack.")
  parser.add_argument("--window_size", type=int, nargs=2, default=(50,50), help="The size of the window for tiling")
  parser.add_argument("--stride", type=int, default=10, help="The stride for tiling")
  args = parser.parse_args()
  
  args.input_directory="/athena/listonlab/store/dje4001/lightsheet/puja_gcamp/stitched/20220925_15_33_31_Cage_AnimalF83_VirusAAVrgNAcAAV1GCAMP7_PUJAPAREKH/20220925_15_33_31_Cage_AnimalF83_VirusAAVrgNAcAAV1GCAMP7_PUJAPAREKH/test/"
  args.output_directory="/athena/listonlab/store/dje4001/lightsheet/puja_gcamp/enhanced/20220925_15_33_31_Cage_AnimalF83_VirusAAVrgNAcAAV1GCAMP7_PUJAPAREKH/"
  args.window_size=(100,100)
  args.stride=(5,5)

  # Get list of tiffs
  string_search=args.input_directory+"**/*.tif*"
  image_paths=glob.glob(string_search,recursive=True)
  output_paths=[sub.replace(args.input_directory,args.output_directory) for sub in image_paths]

  window_size = tuple(args.window_size)
  stride = args.stride

  for (image,output_image) in zip(image_paths,output_paths):
      #image_oh,re_image_oh=enhance_image(image,output_image,window_size,stride,1,0)
      image_oh=imread(image)
      image_oh=np.array(image_oh)
      (rows,columns)=image_oh.shape
      canvas=np.zeros((closestNumber(rows, 2),closestNumber(columns,2)))
      canvas[0:rows,0:columns]=image_oh
      tile_num=(closestNumber(rows, 2)*closestNumber(columns, 2))/(2*2)
      canvas2=canvas.reshape(2,2,int(tile_num))
      
      updated_tiles=[]
      for tile in canvas2:
          updated_tiles.append(normalize_local(tile))
      
      updated_tiles=np.array(updated_tiles)
      updated_tiles_F1=updated_tiles.reshape((closestNumber(rows, 2),closestNumber(columns, 2)))
    
      #flip image and do again
      image_oh=image_oh.T
      (rows,columns)=image_oh.shape
      canvas=np.zeros((closestNumber(rows, 2),closestNumber(columns,2)))
      canvas[0:rows,0:columns]=image_oh
      tile_num=(closestNumber(rows, 2)*closestNumber(columns, 2))/(2*2)
      canvas2=canvas.reshape(2,2,int(tile_num))
      
      updated_tiles=[]
      for tile in canvas2:
          updated_tiles.append(normalize_local(tile))
      
      updated_tiles=np.array(updated_tiles)
      updated_tiles_F2=updated_tiles.reshape((closestNumber(rows, 2),closestNumber(columns, 2)))
    
      final=updated_tiles_F1+updated_tiles_F2.T
    
    
    
      plt.figure()
      imshow(adjust_contrast(updated_tiles_F1,alpha=100,beta=50),cmap='gray')
      plt.show()
      
      plt.figure()
      imshow(adjust_contrast(updated_tiles_F2.T,alpha=100,beta=50),cmap='gray')
      plt.show()
      
      plt.figure()
      imshow(adjust_contrast(final,alpha=100,beta=50),cmap='gray')
      plt.show()
      ipdb.set_trace()



"""
  # Use a ThreadPoolExecutor to process the images in parallel
  with ThreadPoolExecutor() as executor:
      # Submit the enhance_image function for each image in the stack to the executor
      futures = [executor.submit(enhance_image, image, output_image, window_size, stride,1.5,10) for (image,output_image) in zip(image_paths,output_paths)]

      # Iterate over the completed futures to get the contrast-enhanced images
      contrast_enhanced_images = [future.result() for future in futures]





canvas3=[]
for image in canvas2:
    canvas3.append(adjust_contrast(image))"""