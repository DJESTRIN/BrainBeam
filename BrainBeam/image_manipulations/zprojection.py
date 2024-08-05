#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate Max intensity projection image, and perform validation of classifier
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

def add_gt(base_dir):
    search_string=base_dir+'*.txt*'
    gt_file=glob.glob(search_string)
    gt_file=gt_file[0]
    coordinates=np.loadtxt(gt_file,dtype=np.float)
    
    #Eliminate out of range gt coordinates (greater than 400)
    if coordinates.ndim>1:
        
        final_coordinates=[]
        for i,row in enumerate(coordinates):
            
            if row[2]<400 and row[1]<400:
                final_coordinates.append(row)

        coordinates=np.asarray(final_coordinates)
        
    else:
        if coordinates[2]<400 and coordinates[1]<400:
            coordinates=np.asarray(coordinates)
      
    return coordinates

def add_lifecanvas_json(base_dir):
    search_string=base_dir+'*.json'
    lc_file=glob.glob(search_string)
    f=open(lc_file[0])
    lc_coords=json.load(f)
    lc_coords=np.array(lc_coords)
    return lc_coords
    
def eliminate_double_counts(list_of_cells,pixel_threshold):
    final_list=list_of_cells
    rows_to_be_deleted=[]
    for i,c1 in enumerate(list_of_cells[:-1]):
        for ii,c2 in enumerate(list_of_cells[1:]):
            if (i-1)!=ii: #Making sure it is not the same exact cell 
                distance=math.dist(c1,c2)
                
                if distance<pixel_threshold:
                    new_point=(c1+c2)/2
                    final_list[i]=new_point
                    rows_to_be_deleted.append([ii+1])

    rows_to_be_deleted=np.asarray(rows_to_be_deleted)
    rows_to_be_deleted=np.unique(rows_to_be_deleted)
    try:
        if rows_to_be_deleted.ndim>1:
            final_list=np.delete(final_list,(rows_to_be_deleted),axis=0)
    except:
        ipdb.set_trace()    
    return final_list

def generate_grid(folder_path):
    images=glob.glob(folder_path+"output*/zmax_gt_lc.png")
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


""" Manual mode """
subjects=['/athena/listonlab/store/dje4001/lightsheet/test_segmentation_f1/redcloudrun/test2/*/']

all_folders=[]
for subject in subjects:
    all_folders.append(glob.glob(subject+'Ex_647_Em_680*/'))

image_folders=[item for subjects in all_folders for item in subjects]

F1=[]
All_info=[]
Radius=[]
for folder in image_folders:
    lc_folders=glob.glob(folder+'output*/')
    
    for lc_folder in lc_folders:
        
        os.chdir(folder)
        search_string=folder+'images/*.tif*'
        tiff_images=glob.glob(search_string)
        zimage=ZProjection(tiff_images)
        gt_coors=add_gt(folder+'gt/')
        lc_coors=add_lifecanvas_json(lc_folder)
        
        #Get info from folder name
        sample_name,threshold_info=lc_folder.split('output')
        threshold_info,_=threshold_info.split('/')
        classifier_threshold,detector_threshold=threshold_info.split('_')
        
        
        #Eliminate double counts and run diagnostics
        if lc_coors.ndim>1 and lc_coors.size!=3:
            if len(lc_coors)<10000: #For extremely long lists of cells, there is no point 
                #eliminate double counts
                lc_coors=eliminate_double_counts(lc_coors,20)
                
                #Loop over radius thresholds:
                for radius in range(10,60,10):
                    #Get F1 score
                    F1.append(diagnostics(lc_coors,gt_coors,radius))
                    All_info.append([sample_name,classifier_threshold,detector_threshold,threshold_info])
                    Radius.append(radius)
            else:
                for radius in range(10,60,10):
                    F1.append(0)
                    All_info.append([sample_name,classifier_threshold,detector_threshold,threshold_info])
                    Radius.append(radius)
        else:
            for radius in range(10,60,10):
                F1.append(diagnostics(lc_coors,gt_coors,radius))
                All_info.append([sample_name,classifier_threshold,detector_threshold,threshold_info])
                Radius.append(radius)
            
        
        #Plot and save z projection
        plt.figure(figsize=(10,10))
        plt.imshow(zimage,cmap='gray')
        title_string="Classifier Threshold: "+str(int(classifier_threshold)/100)+ "  Detector Threshold: "+str(int(detector_threshold)/100)
        plt.title(title_string,fontsize=20)
            
        #Plot lifecanvas predictions
        if lc_coors.size>0:
            if lc_coors.ndim>1:
                plt.scatter(x=lc_coors[:,0],y=lc_coors[:,1],color="r")
            else:
                plt.scatter(x=lc_coors[0],y=lc_coors[1],color="r")
        
        #plot ground truth
        if gt_coors.ndim>1 and gt_coors.size>0:
            #circ = plt.Circle((gt_coors[:,2], gt_coors[:,1]),10 , fill = False )
            plt.scatter(x=gt_coors[:,2],y=gt_coors[:,1],facecolors='none',edgecolors="g",s=400)
        elif gt_coors.ndim==1 and gt_coors.size>0:
            try:
                plt.scatter(x=gt_coors[2],y=gt_coors[1],facecolors='none',edgecolors="g",s=400)
            except:
                ipdb.set_trace()
        
        plt.axis('off')
        plt.savefig(lc_folder+'zmax_gt_lc.png')
        plt.close()
        print(folder)
    generate_grid(folder)


#Generate final dataframe:
All_info=np.asarray(All_info)
DF_all=pd.DataFrame({'sample':All_info[:,0],'classifier_threshold':All_info[:,1],'detector_threshold':All_info[:,2],'thresholds':All_info[:,3],'Radius':Radius,'F1':F1})
DF_all.to_csv('/athena/listonlab/scratch/dje4001/classifier_validation_results.csv') 


#Trouble shoot
"""
folder='/athena/listonlab/store/dje4001/lightsheet/test_segmentation_f1/redcloudrun/test2/20220926_17_49_34_CAGE4094795_ANIMAL01_VIRUSRABIES_CORTEXPERIMENTALEx_647_Em_680/Ex_647_Em_6802/'
lc_folder='/athena/listonlab/store/dje4001/lightsheet/test_segmentation_f1/redcloudrun/test2/20220926_17_49_34_CAGE4094795_ANIMAL01_VIRUSRABIES_CORTEXPERIMENTALEx_647_Em_680/Ex_647_Em_6802/output24_99/'

"""