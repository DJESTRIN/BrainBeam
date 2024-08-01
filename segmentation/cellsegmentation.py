
"""
SA Model classes test script
"""
import pickle 
import argparse
import os
import sys

sys.path.insert(0,'/home/dje4001/LIGHTSHEET_CLUSTER/SA_files/')

parser=argparse.ArgumentParser()
parser.add_argument('--lifecanvas_code_directory',type=str,required=True)
parser.add_argument('--input_dir',type=str,required=True)
parser.add_argument('--output_dir',type=str,required=True)

if __name__=='__main__':
    args=parser.parse_args()
    lifecanvas_code_directory=args.lifecanvas_code_directory
    sample_directory=args.input_dir
    output_directory=args.input_dir+"cell_detect_test.json"
    os.chdir(lifecanvas_code_directory)
    from ModelClasses import Model_CNNDetect_CNNClassify # This package must be obtained from lifecanvas
    model = Model_CNNDetect_CNNClassify(
        detectorPath="/home/dje4001/LIGHTSHEET_CLUSTER/SA_files/Models/tf-models/ViralFluorescence_detect_2021_5_4_85",
        classifierPath = "/home/dje4001/LIGHTSHEET_CLUSTER/SA_files/Models/tf-models/ViralFluorescence-classify",
        classificationThreshold=0.9,
        detectionThreshold=0.1,
        modelName="Modelforvirus",
        modelDescription="A Model made by lifecanvas",)

    with open('/home/dje4001/LIGHTSHEET_CLUSTER/SA_files/Models/ViralFluorescence_model.pkl','wb') as f:
        pickle.dump(model,f)
        
    print(str(sample_directory))
    model.execute_on_dataset(data_path=sample_directory, out_path=output_directory, z_step=4)
