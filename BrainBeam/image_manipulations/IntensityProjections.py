#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate Axial View Average Intensity Projection

Take sum of pixels and then divide by length of images
"""
import glob
import tqdm
import ipdb
from skimage.io import imread
import matplotlib.pyplot as plt
import numpy as np

def IntensityProjection(directory):
    images=glob.glob(directory+'*.tif*')
    for i,image in tqdm.tqdm(enumerate(images),total=len(images)):
        if i==0:
            image_final=imread(image)
            image_final=np.array(image_final)
            image_final=image_final[...,np.newaxis]
        else:
            image_oh=imread(image)
            image_oh=np.array(image_oh)
            image_oh=image_oh[...,np.newaxis]
            precalculation=np.concatenate((image_final,image_oh),axis=2)
            image_final=np.max(precalculation,axis=2)
            image_final=image_final[...,np.newaxis]
    return image_final


#def display_counts(directory):
    


directory='/athena/listonlab/scratch/dje4001/rabies_cort_experimental/lightsheet/stitched/20220923_14_38_30_CAGE3752774_ANIMAL05_VIRUSRABIES_CORTEXPERIMENTAL/Ex_647_Em_680/'       
MIP=IntensityProjection(directory)
plt.figure(figsize=(10,10))
plt.imshow(MIP,cmap='gray')
plt.savefig('/home/dje4001/lightsheet_cluster/exampleMIP.pdf')