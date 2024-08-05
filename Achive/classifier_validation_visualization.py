#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validation experiment:
    Use optuna to find the best thresholds
"""
import numpy as np
import math
import sys
sys.path.append("/home/dje4001/LIGHTSHEET_CLUSTER/SA_files/")
from ModelClasses import Model_CNNDetect_CNNClassify # This package must be obtained from lifecanvas
import glob,os
import json
import pickle
import numpy as np
import ipdb
import matplotlib.pyplot as plt
import tqdm
import shutil

subjects=glob.glob("/athena/listonlab/store/dje4001/lightsheet/test_segmentation_f1/redcloudrun/test2/*/")
all_folders=[]
for subject in subjects:
    all_folders.append(glob.glob(subject+'Ex_647_Em_680*/'))

data_folders=[item for subjects in all_folders for item in subjects]
    
def MoveResults(folder,detector_threshold,classifier_threshold):
    folder_new=folder+"output"+str(int(detector_threshold*100))+'_'+str(int(classifier_threshold*100))+'/'
    folder=folder+'images/'
  
    if not os.path.exists(folder_new):
        os.makedirs(folder_new)
        
    #Find all files that need to be moved
    file_list=glob.glob(folder+'*.jpg')+glob.glob(folder+'*.pkl')+glob.glob(folder+'*.json')+glob.glob(folder+'*.pdf')
    destinations=[file.replace(folder,folder_new) for file in file_list]
    for i,file in enumerate(destinations):
        shutil.move(file_list[i],file)


for folder in data_folders:
    for detector_threshold in np.linspace(0,0.99,5):
        for classifier_threshold in np.linspace(0,0.99,5):
                folder2=folder+"images/"
                output_folder=folder2+"cell_detect_test.json"

                model = Model_CNNDetect_CNNClassify(
                    detectorPath="/home/dje4001/LIGHTSHEET_CLUSTER/SA_files/Models/tf-models/ViralFluorescence_detect_2021_5_4_85",
                    classifierPath = "/home/dje4001/LIGHTSHEET_CLUSTER/SA_files/Models/tf-models/ViralFluorescence-classify",
                    classificationThreshold=classifier_threshold,
                    detectionThreshold=detector_threshold,
                    modelName="Modelforvirus",
                    modelDescription="A Model made by lifecanvas",)

                with open('/home/dje4001/LIGHTSHEET_CLUSTER/SA_files/Models/ViralFluorescence_model.pkl','wb') as f:
                    pickle.dump(model,f)
                 
                """ Run model """
                model.execute_on_dataset(data_path=folder2, out_path=output_folder, z_step=4)
                
                """ Move Results to new folder"""
                MoveResults(folder,detector_threshold,classifier_threshold)
