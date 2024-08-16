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
import ipdb
from tqdm import tqdm

def tile(image_path, slice_folder, block_size,z):
    img = Image.open(image_path)
    w, h = img.size
    grid = product(range(0, h-h%block_size, block_size), range(0, w-w%block_size, block_size))
    for i, j in grid:
        drop_path = slice_folder + str(i) + '_' + str(j) +"/"
        box = (j, i, j+block_size, i+block_size)
        
        # Create subfolder if not created and save image to it
        if os.path.exists(drop_path):
            out = drop_path+"image"+str(z)+".tiff"
            img.crop(box).save(out)
        else:
            os.mkdir(drop_path)
            out = drop_path+"image"+str(z)+".tiff"
            img.crop(box).save(out)
        

def divide_image_stack(stitched_input,output_parent,block_size):
    image_search=stitched_input+'*.tif*'
    images=glob.glob(image_search) #Does glob sort the files correctly??
    images=sorted(images)
    if len(images)<3500:
        ipdb.set_trace()
 
    slices=range(0,len(images)-len(images)%block_size,block_size)
    for slice_start,slice_stop in zip(slices[:-1],slices[1:]):
        print(f'This is the start: {slice_start}, this is the stop: {slice_stop}')
        # Create subfolder based on slice
        front,back=output_parent.split('Ex_')
        slice_folder=front+"/Ex_"+back+"/slice"+str(slice_start)+"/"
        if not os.path.exists(slice_folder):
            os.mkdir(slice_folder)
        
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
    
    if not os.path.exists(args.output_dir):
        os.mkdir(args.output_dir)
        
    # Divide the image
    divide_image_stack(args.input_dir,args.output_dir,500)











