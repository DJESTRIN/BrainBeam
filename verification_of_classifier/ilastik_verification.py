#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verify ilastik classification:
    (1) Loop through all tif sequences to get ilastik numpy output
    (2) Import all numpy files and corresponding text files for gt
    (3) Calculate F1 score using gt and thresholded probabilite 0.05=>
        Get a line (x=threshold,y=f1) for each sample
        Average the line to determine best overall thresholds F1 score. 
        
"""
#Package dependencies
import ipdb
import numpy as np
import os, glob
from skimage.measure import regionprops as rp
from skimage.measure import label
import matplotlib.pyplot as plt
from tqdm import tqdm


#Custom Euclidian distance formula
def distance(x1,x2,y1,y2,z1,z2):
    g=(x2-x1)**2+(y2-y1)**2+(z2-z1)**2
    return np.sqrt(g)


#Loop through all training images to get ilastik output
data_path=["/athena/listonlab/store/dje4001/lightsheet/test_segmentation_f1/rabies_cort_experimental_training_data/"]
Thresholds=[i/100 for i in range(1,100,5)]

F_ALL=[]
for root,dirs,files in os.walk(data_path[0]):
    for file in files:
        if "npy" in file:
            
            #Get ground truth file
            for file2 in files:
                if "txt" in file2:
                    gt_path=root+"/"+file2

            #load in segmentation and ground truth
            largemat=np.load(root+"/"+file)
            gt=np.loadtxt(gt_path)
            cellbodies=np.squeeze(largemat[:,:,:,0])
            cellbodies_copy=np.copy(cellbodies)
            
            #loop through thresholds
            Fone=[]
            for threshold in tqdm(Thresholds):
                #Apply threshold
                cellbodies_copy[np.where(cellbodies>threshold)]=1
                cellbodies_copy[np.where(cellbodies<threshold)]=0
                
                #Group similar values
                labels=label(cellbodies_copy)
                regions=rp(labels)
                
                #Get coordinates of proposed points
                points=[]
                for region in regions:
                    points.append(region.centroid)
                 
                #Get the number of tp, fp and fn
                tp=0
                gt_copy=np.copy(gt)
                for point in points:
                    for i,cell in enumerate(gt_copy):
                        de=distance(point[1],cell[0],point[2],cell[1],point[0],cell[2])
                        if de<8:
                            tp+=1
                            #Once ground truth cell is accounted for, remove from the list
                            gt_copy=np.delete(gt_copy,i,axis=0)
                            break
                
                fp=len(points)-tp
                fn=len(gt)-tp
                fone_oh=(2*tp)/((2*tp)+fp+fn)
                Fone.append([threshold,fone_oh])

            # F all contains all all F one scores
            F_ALL.append(Fone)
                
                
        


