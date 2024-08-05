import numpy as np 
import nrrd 
import argparse
import ipdb
from PIL import Image
import os



def convert(full_path_nrrd,full_path_outputfolder):
    readdata, header = nrrd.read(full_path_nrrd)
    R2=readdata+1
    R2=np.log(R2)
    R2=(R2-R2.min())/(R2.max()-R2.min())*255
    counter=0
    for image in R2:
        im=Image.fromarray(image)
        filename=os.path.join(full_path_outputfolder,f'{counter}.tiff')
        im.save(filename)
        print(filename)
        counter+=1

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_nrrd_file',type=str)
    parser.add_argument('--output_folder',type=str)
    args=parser.parse_args()
    convert(args.input_nrrd_file,args.output_folder)