# -*- coding: utf-8 -*-
"""
Find and replace empty tiff files. 
"""
import os
import numpy as np
from PIL import Image
import argparse

def seek_and_destroy(path):
    for directory in os.walk(path):
       images_in_stack=[]
       
       for file in os.listdir(directory[0]):
           if file.endswith('.tiff') or file.endswith('.png'):
               images_in_stack.append((directory[0] + "/" + file))
     
       #print(images_in_stack)
       for image in images_in_stack:
           if os.stat(image).st_size==0:
              new_image=np.zeros((2000,1600))
              new_empty_image=Image.fromarray(new_image)
              new_empty_image.save(image)

parser=argparse.ArgumentParser()
parser.add_argument('--pathway',type=str,required=True)

if __name__=="__main__":
    args=parser.parse_args()
    seek_and_destroy(args.pathway)
    print("done")
