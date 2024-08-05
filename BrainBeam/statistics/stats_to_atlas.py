#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 20 14:13:04 2023

@author: dje4001
"""

from skimage.io import imread, imsave
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats
from princeton_ara import *
import pandas as pd
import os

#Image drop directory
os.chdir("/athena/listonlab/scratch/dje4001/pseudorabies_figures/atlas_images/")

#Set up ARA tree
atlas_json_file = '/home/dje4001/CloudReg/cloudreg/scripts/ARA_stuff/ara_ontology.json'
with open(atlas_json_file,'r') as infile:
    ontology_dict = json.load(infile)
d=Graph(ontology_dict)

#Get average data
df=pd.read_csv("/athena/listonlab/scratch/dje4001/pseudorabies_average.csv")
dfnp=np.asarray(df)
controls=dfnp[np.where(dfnp[:,1]=='Vehicle')]
experimental=dfnp[np.where(dfnp[:,1]!='Vehicle')]
ids=[]
for location in controls[:,2]:
    ids.append(d.get_id(location))
ids=np.array(ids)

experimental_ids=[]
for location in experimental[:,2]:
    experimental_ids.append(d.get_id(location))
experimental_ids=np.array(experimental_ids)

#Loop through each image of the ARA atlas tif sequence
atlas_path="/athena/listonlab/scratch/dje4001/cloudreg_base/CloudReg/cloudreg/registration/atlases/ara_annotation_10um.tif"
atlas_stack=imread(atlas_path)
atlas_stack=np.squeeze(np.array(atlas_stack))
atlas_stack=atlas_stack.astype('float')


name_counter=0
for sn in range(1,atlas_stack.shape[2]):
    if (sn%50)==0:
        slicea=atlas_stack[:,:,sn]
        background=stats.mode(slicea)
        background=background[0][0][0]
        slicea[np.where(slicea==background)]=np.nan        
        slicec=np.copy(slicea)
        counter=1
        for i in np.unique(slicea):
            slicec[np.where(slicea==i)]=counter
            counter+=1.100000000000000123
        
        plt.figure()
        plt.imshow(slicec.T,cmap='gray')
        plt.axis('off')
        plt.tight_layout()
        plt.savefig("atlas"+str(name_counter)+".pdf")
        name_counter+=1

#Plot vehicle and CORT data
name_counter=0
for sn in range(1,atlas_stack.shape[2]):
    if (sn%50)==0:
        slicea=atlas_stack[:,:,sn]
        background=stats.mode(slicea)
        background=background[0][0][0]
        slicea[np.where(slicea==background)]=np.nan        
        slicec=np.copy(slicea)
        for i in np.unique(slicea):
            value=controls[np.where(ids==i),3]
            try:
                slicec[np.where(slicea==i)]=value
            except:
                slicec[np.where(slicea==i)]=np.nan
        
        plt.figure()
        plt.imshow(slicec.T,cmap='Blues')
        plt.axis('off')
        plt.tight_layout()
        plt.savefig("vehicle"+str(name_counter)+".pdf")
        name_counter+=1


#Plot CORT samples
name_counter=0
for sn in range(1,atlas_stack.shape[2]):
    if (sn%50)==0:
        slicea=atlas_stack[:,:,sn]
        background=stats.mode(slicea)
        background=background[0][0][0]
        slicea[np.where(slicea==background)]=np.nan        
        slicec=np.copy(slicea)
        for i in np.unique(slicea):
            value=experimental[np.where(experimental_ids==i),3]
            try:
                slicec[np.where(slicea==i)]=value
            except:
                slicec[np.where(slicea==i)]=np.nan
        
        plt.figure()
        plt.imshow(slicec.T,cmap='Oranges')
        plt.axis('off')
        plt.tight_layout()
        plt.savefig("experimental"+str(name_counter)+".pdf")
        name_counter+=1

#Plot vehicle and CORT data
name_counter=0
for sn in range(1,atlas_stack.shape[2]):
    if (sn%50)==0:
        slicea=atlas_stack[:,:,sn]
        background=stats.mode(slicea)
        background=background[0][0][0]
        slicea[np.where(slicea==background)]=np.nan     
        
        #Plot Vehicle
        slicec=np.copy(slicea)
        for i in np.unique(slicea):
            value=controls[np.where(ids==i),3]
            try:
                slicec[np.where(slicea==i)]=value
            except:
                slicec[np.where(slicea==i)]=np.nan
        
        plt.figure()
        plt.imshow(slicec.T,cmap='Blues')
        plt.axis('off')
        plt.tight_layout()
      
        #Plot CORT experimental
        slicec=np.copy(slicea)
        for i in np.unique(slicea):
            value=experimental[np.where(experimental_ids==i),3]
            try:
                slicec[np.where(slicea==i)]=value
            except:
                slicec[np.where(slicea==i)]=np.nan
        

        plt.imshow(slicec.T,cmap='Oranges',alpha=0.5)
        plt.axis('off')
        plt.tight_layout()
        plt.savefig("combined"+str(name_counter)+".pdf")
        name_counter+=1
