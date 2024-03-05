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
#from ModelClasses import Model_CNNDetect_CNNClassify # This package must be obtained from lifecanvas
import glob,os
import json
import pickle
import numpy as np
import ipdb
import matplotlib.pyplot as plt
import tqdm
plt.switch_backend('agg')

Parent_directory="/athena/listonlab/store/dje4001/lightsheet/test_segmentation_f1/rabies_cort_experimental_training_data/"

def diagnostics(proposed_cell_list, ground_truth,pixel_threshold):
    """Takes ground truth ROIs and proposed ROIs and calculates F1 score"""
    TP=0
    FP=0
    if ground_truth.ndim>1:
        for pc in proposed_cell_list:
            Found=False
            for gc in ground_truth:
                gc=np.asarray([gc[2],gc[1],gc[0]])
                distance=math.dist(pc,gc)
                if distance<pixel_threshold and distance>=0:
                    Found=True
                    TP+=1
            if Found==False:
                FP+=1
    else:
        for pc in proposed_cell_list:
            try:
                distance=math.dist(pc,ground_truth)
            except:
                if pc.size!=ground_truth.size:
                    F1=np.nan
                    return F1
                else:
                    ipdb.set_trace()
            if distance<pixel_threshold and distance>=0:
                TP+=1
                
    FN=len(ground_truth)-TP
    if FN<1:
        FN=0
    
    if (TP+FN)==0 or (TP+FP)==0:
        F1=np.nan
        return F1
    
    Precision=(TP)/(TP+FP)
    Recall=(TP)/(TP+FN)
    if (Precision+Recall)==0:
        F1=0
    else:
        F1=2*(Precision*Recall)/(Precision+Recall)
    if F1>1:
        ipdb.set_trace()
    return F1

def cell_coexpression(cell_list1,cell_list2,pixel_threshold):
    """Checks for coexpression. also used to eliminate double counts"""
    flag=np.zeros(len(cell_list1))
    index=0
    for c1 in cell_list1:
        for c2 in cell_list2:
            distance=math.dist(c1,c2)
            if distance<pixel_threshold:
                if distance>0:
                    flag[index]=1
        index+=1
    return flag

# def objective(trial):
#     detector_threshold=trial.suggest_float('detector_threshold', 0, 1)
#     classifier_threshold=trial.suggest_float('classifier_threshold', 0, 1)

if __name__=="__main__":
    from ModelClasses import Model_CNNDetect_CNNClassify
    F1_list=[]
    for detector_threshold in np.linspace(0,0.99,11):
        for classifier_threshold in np.linspace(0,0.99,11):
            print("This is the detector threshold:"+str(detector_threshold))
            print("This is the classifier threshold:"+str(classifier_threshold))
            for subdir,dirs,files in os.walk(Parent_directory):
                print(subdir)
                if "Em_680/Ex" in subdir:
                    """ Set up model """
                    print("STARTINGNOW")
                    output_directory=subdir+"cell_detect_test.json"
                    model = Model_CNNDetect_CNNClassify(
                        detectorPath="/home/dje4001/LIGHTSHEET_CLUSTER/SA_files/Models/tf-models/ViralFluorescence_detect_2021_5_4_85",
                        classifierPath = "/home/dje4001/LIGHTSHEET_CLUSTER/SA_files/Models/tf-models/ViralFluorescence-classify",
                        classificationThreshold=0.5,
                        detectionThreshold=0.5,
                        modelName="Modelforvirus",
                        modelDescription="A Model made by lifecanvas",)
                
                    with open('/home/dje4001/LIGHTSHEET_CLUSTER/SA_files/Models/ViralFluorescence_model.pkl','wb') as f:
                        pickle.dump(model,f)
                     
                    """ Run model """
                    model.execute_on_dataset(data_path=subdir, out_path=output_directory, z_step=4)
            
                    """ get ground truth data """
                    searchstring=subdir+"/*txt"
                    gt_files=glob.glob(searchstring)
                    gt=np.loadtxt(gt_files[0])
                    
                    
                    f=open(output_directory)
                    proposed_cell_list=json.load(f)
            
                    if gt.shape!=(3,):
                        F1=diagnostics(proposed_cell_list,gt,7)
                        print(F1)
                        F1_list.append([detector_threshold,classifier_threshold,F1])
                        
    F1_list=np.array(F1_list)
    np.save("/athena/listonlab/scratch/dje4001/detection_results.npy",F1_list)
    data=np.load("/athena/listonlab/scratch/dje4001/detection_results.npy")
    
        # return F1_final
    
    # study_name="Rabies-detection-study-6"
    # study = optuna.create_study(study_name=study_name,storage="sqlite:///rabiesdetectionstudy.db")  # Create a new study.
    # study.optimize(objective, n_trials=200)  # Invoke optimization of the objective function.
    
    model = Model_CNNDetect_CNNClassify(detectorPath="/home/dje4001/LIGHTSHEET_CLUSTER/SA_files/Models/tf-models/ViralFluorescence_detect_2021_5_4_85",classifierPath = "/home/dje4001/LIGHTSHEET_CLUSTER/SA_files/Models/tf-models/ViralFluorescence-classify",classificationThreshold=0.5,detectionThreshold=0.5,modelName="Modelforvirus",modelDescription="A Model made by lifecanvas",)