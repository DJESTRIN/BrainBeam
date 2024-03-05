
"""
SA Model classes test script
"""
import sys
sys.path.insert(0,'/home/dje4001/LIGHTSHEET_CLUSTER/SA_files/')
from ModelClasses import Model_DetectOnly
import pickle 

model = Model_DetectOnly(detectorPath = "./Models/tf-models/ViralFluorescence_detect_2021_5_4_85",
        detectionThreshold=0.8,
        modelName="ViralFluorescence (detect only)2",
        modelDescription="A Model made by lifecanvas I think2",)

with open('./Models/ViralFluorescence_model.pkl','wb') as f:
    pickle.dump(model,f)
    
model.execute_on_dataset(data_path="/athena/listonlab/store/dje4001/lightsheet/rabies/20220729_18_49_33_3811494_A#1018_P__Rabies__MPFC_CORT_CONTROL/Ex_647_Em_680/450200/450200_477120/", 
         out_path="/athena/listonlab/store/dje4001/lightsheet/rabies/20220729_18_49_33_3811494_A#1018_P__Rabies__MPFC_CORT_CONTROL/Ex_647_Em_680/450200/450200_477120/cell_detect_test.json",
         z_step=4)
