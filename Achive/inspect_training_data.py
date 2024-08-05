#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Visualize Training data via z projection
"""
from PIL import Image, ImageOps
import numpy as np
import os,glob
import matplotlib.pyplot as plt
from matplotlib.image import imread
import ipdb
import json
import math
import sys
sys.path.append('/home/dje4001/lightsheet_cluster/')
from classifier_validation import diagnostics 
import pandas as pd
import tqdm


plt.close("all")

def ZProjection(image_directories):
    init_image=Image.open(image_directories[0])
    init_image=ImageOps.grayscale(init_image)
    init_image=np.asarray(init_image)
    
    counter=0
    for image_oh in image_directories[1:]:
       image_oh=Image.open(image_oh)
       image_oh=ImageOps.grayscale(image_oh)
       image_oh=np.asarray(image_oh) 
       con_images=np.concatenate((init_image[...,None],image_oh[...,None]),axis=2)
       init_image=np.amax(con_images,axis=2)
       counter+=1
       if counter>=400:
           init_image=init_image[0:400,0:400]
           return init_image
       
    return init_image #This is now the max z projection


def generate_grid(folder_path):
    images=glob.glob(folder_path+"/*/zmax.png")
    fig=plt.figure(figsize=(50,50))
    
    counter=1
    for image in images:
        plt.axis('off')
        img=imread(image)
        ax_oh=fig.add_subplot(5,5,counter)
        ax_oh.imshow(img)
        counter+=1
    
    plt.axis('off')
    fig.tight_layout()
    plt.savefig(folder_path+'grid_results.pdf')
    return


subjects='/athena/listonlab/store/dje4001/lightsheet/fostrapxai9tdtomato/fostrapxai9tdtomato_cohort4_watercontrol/training_data/*/'

all_folders=[]
for subject in glob.glob(subjects):
    all_folders.append(glob.glob(subject+'Ex_647_Em_680*/'))

image_folders=[item for subjects in all_folders for item in subjects]

for folder in tqdm.tqdm(image_folders):
    os.chdir(folder)
    search_string=folder+'*.tif*'
    tiff_images=glob.glob(search_string)
    if len(tiff_images)<3:
        continue
    zimage=ZProjection(tiff_images)
    
    #Plot and save z projection
    plt.figure(figsize=(10,10))
    plt.imshow(zimage,cmap='gray')
    plt.axis('off')
    plt.savefig(folder+'zmax.png')
    #plt.close()
    print(folder)
    
for subject in glob.glob(subjects):
    generate_grid(subject)