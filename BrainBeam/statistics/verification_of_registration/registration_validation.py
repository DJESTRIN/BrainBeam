#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun  1 16:14:24 2023

@author: dje4001
"""
import numpy as np
import sys,os
sys.path.insert(0,'/home/dje4001/CloudReg/')
sys.path.insert(0,'/home/dje4001/lightsheet_cluster/')
from cloudreg.scripts.ARA_stuff.parse_ara import *
from statistics.princeton_ara import *
from PIL import Image
import ipdb
import matplotlib.pyplot as plt

ara_file="/home/dje4001/CloudReg/cloudreg/scripts/ARA_stuff/ara_ontology.json"
with open(atlas_json_file,'r') as infile:
    ontology_dict = json.load(infile)

Tree=Graph(ontology_dict)   
all_children=Tree.get_progeny(nodename='root')

gt = np.genfromtxt('/athena/listonlab/scratch/dje4001/registration_validation/cloudregregistration_gt.csv', delimiter=',')
gt=gt[~np.isnan(gt).any(axis=1)]

image_dir="/athena/listonlab/scratch/dje4001/registration_validation/images/"
os.chdir(image_dir)

def DetermineRelationship(predicted,gt,jumps):
    df=[]
    i=0
    while i < jumps:
        # Get all children of the current gt
        try:
            gt_children=Tree.get_progeny(nodename=gt)
            if gt==predicted:
                df.append([1])
                
            elif predicted in gt_children[0]:
                df.append([1])
                
            else:
                df.append([0])
            
            gt=Tree.get_parent(gt)
        except:
            df.append([np.nan])

        i+=1
    return df

def diagnostics(groundtruth_data,path_to_registered_images,all_children):
    DF=[]
    names=[]
    for row in groundtruth_data:
        cageid=int(row[0])
        subjectid=int(row[1])
        original_path=os.getcwd()
        for root,dirs,files in os.walk(path_to_registered_images):
            for dirname in dirs:
                string1=str(cageid)+'_'+str(subjectid)
                if string1 in dirname:
                    image_name=str(int(row[4]))+".tiff"
                    full_image_name=root+dirname+'/'+image_name
                    im = Image.open(full_image_name)
                    imarray=np.asarray(im)
                    predicted_id=imarray[int(row[3]),int(row[2])]
                    gt_id=int(row[5])
                    
                    ## Get node name from ID
                    gt_name=all_children[0][all_children[1].index(gt_id)]
                    predicted_name=all_children[0][all_children[1].index(predicted_id)]
                    names.append([gt_name,predicted_name])
                    #Determion relationship and add to DF
                    DF.append(DetermineRelationship(predicted_name,gt_name,10))
    return DF,names


DF,names=diagnostics(gt,image_dir,all_children)      
DF=np.asarray(DF)
DF=DF[:,~np.all(np.isnan(DF), axis=0)]
print(np.nanmean(DF,axis=0))     

all_children=Tree.get_progeny(nodename='root')
random_choice=1/len(all_children[0])

se=np.nanstd(DF,axis=0)/np.nansqrt(np.nansize(DF,axis=0))

plt.figure(figsize=(10,10))
plt.xlabel('Atlas level', fontweight='bold',  fontsize='17')
plt.ylabel('Registration Accuracy', fontweight='bold',  fontsize='17')
plt.hlines(y=0.8, xmin=-1,xmax=10,colors='black', linestyles='--', lw=1.5)
plt.hlines(y=random_choice, xmin=-1,xmax=10,colors='red', linestyles='--', lw=2)
plt.errorbar(x=range(0,len(se)),y=np.nanmean(DF,axis=0),yerr=se)
plt.scatter(x=range(0,len(se)),y=np.nanmean(DF,axis=0),s=100)
plt.xlim(-0.1,8)
plt.ylim(-0.1,1.1)


