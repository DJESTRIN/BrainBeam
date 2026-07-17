#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Divide Images
https://stackoverflow.com/questions/5953373/how-to-split-image-into-multiple-pieces-in-python
"""
import os,glob
import argparse
from PIL import Image
from itertools import product
from tqdm import tqdm

def tile(image_path, slice_folder, block_size,z):
    with Image.open(image_path) as img:
        w, h = img.size
        grid = product(range(0, h-h%block_size, block_size), range(0, w-w%block_size, block_size))
        for i, j in grid:
            drop_path = os.path.join(slice_folder, f'{i}_{j}')
            box = (j, i, j+block_size, i+block_size)

            os.makedirs(drop_path, exist_ok=True)
            out = os.path.join(drop_path, f'image{z:06d}.tiff')
            img.crop(box).save(out)
        

def divide_image_stack(stitched_input,output_parent,block_size):
    image_search=os.path.join(stitched_input, '*.tif*')
    images=glob.glob(image_search) #Does glob sort the files correctly??
    images=sorted(images)
 
    for slice_start in range(0, len(images), block_size):
        slice_stop = min(slice_start + block_size, len(images))
        print(f'This is the start: {slice_start}, this is the stop: {slice_stop}')
        # Create subfolder based on slice
        slice_folder=os.path.join(output_parent, f'slice{slice_start}')
        os.makedirs(slice_folder, exist_ok=True)
        
        # Loop through images in the current slice and tile them
        for z in tqdm(range(slice_start,slice_stop)):
            image_oh=images[z]
            tile(image_oh,slice_folder,block_size,z)
        

if __name__=='__main__':
    #Parse inputs
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", type=str, required=True,
                        help="Input directory")
    parser.add_argument("--output_dir", type=str,
                        help="output_directory")
    args = parser.parse_args()
    
    os.makedirs(args.output_dir, exist_ok=True)
        
    # Divide the image
    divide_image_stack(args.input_dir,args.output_dir,500)










