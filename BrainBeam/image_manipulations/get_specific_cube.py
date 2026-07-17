#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" Downsample Image Stack """
from skimage.io import imread, imsave
from scipy.ndimage import zoom
import numpy as np
import glob
import os
import re
from multiprocessing import Pool
import warnings
import random
import argparse
warnings.filterwarnings("ignore")

class generate_train_data(object):
    def __init__(self, input_path, output_path,*args):
        #input path contains all channels for a single sample
        #output path should be a folder in storage. 
        self.input_path=os.path.abspath(input_path)
        self.output_path=os.path.abspath(output_path)
        
        #Get image list
        self.image_log=glob.glob(os.path.join(self.input_path,'*.tif*'))
        self.image_log=sorted(self.image_log,key=self.custom_sort)
        
        
        #Get image properties
        image_oh=imread(self.image_log[0])
        (self.x,self.y)=image_oh.shape
        self.z=len(self.image_log)

        
    def forward(self,*args):
        if not args:
            self.get_cubes()
        else:
            self.get_cubes(*args)
        self.make_output_dirs()
        self.grab_cube()
        
    def get_cubes(self,*args):
        if not args:
            # Generates 15 cube data sets for the given sample. 
            cubes=[]
            for u in range(15):
                x,y,z=random.randint(0,(self.x-500)),random.randint(0,(self.y-500)),random.randint(0,(self.z-500))
                cube_oh=[x,x+500,y,y+500,z,z+500]
                cubes.append(cube_oh)
            
            self.cubes=cubes
            
        else:
            cubes=list(args)
            if (
                len(cubes)==1
                and isinstance(cubes[0], (list, tuple, np.ndarray))
                and cubes[0]
                and isinstance(cubes[0][0], (list, tuple, np.ndarray))
            ):
                cubes=list(cubes[0])

            self.cubes=[list(cube_oh) for cube_oh in cubes]
        return
    
    def make_output_dirs(self):
        #Generates a new path for each cube
        os.makedirs(self.output_path, exist_ok=True)
        for u in range(len(self.cubes)):
            output_sub=os.path.join(self.output_path, str(u))
            os.makedirs(output_sub, exist_ok=True)
        
    def custom_sort(self,x):
        return int(re.sub(r'[^0-9]','',(os.path.basename(x))))

    def parallel_crop(self,x):
        filename=x[0]
        cube=x[1]
        output_num=x[2][0]
        output_path=os.path.join(self.output_path, str(output_num))
        image_oh=imread(filename)
        crop_image_oh=image_oh[cube[0]:cube[1],cube[2]:cube[3]]
        imsave(os.path.join(output_path, os.path.basename(filename)),crop_image_oh)
        return

    def grab_cube(self):
        self.cubes=np.array(self.cubes)
        self.cubes=np.atleast_2d(self.cubes)
        for i,cube in enumerate(self.cubes):
            #Loop through images on z stack
            self.image_log_oh=self.image_log[cube[4]:cube[5]]
            cube_repeated=np.tile(np.array(cube),(cube[5]-cube[4],1))
            cube_repeated=cube_repeated.tolist()
            
            output_repeated=np.tile(np.array(i),(cube[5]-cube[4],1))
            output_repeated=output_repeated.tolist()
            inputs=list(zip(self.image_log_oh,cube_repeated,output_repeated))
            with Pool() as p:
                p.map(self.parallel_crop,inputs)
                
        return
    
    def parrallel_downsample(self,x):
        filename=x[0]
        output_path=x[1]
        image_oh=np.array(imread(filename))
        ds_image_oh=zoom(image_oh,(0.08,0.08))
        imsave(os.path.join(output_path,f"{x[2]}.tif"),ds_image_oh)
        return
    
    def custom_sort_ds(self,x):
        return int(x[:-4])
    
    def downsample_image(self):
        # downsample images in parrallel
        inputs=[]
        for k,filename in enumerate(self.image_log):
            inputs.append([filename,self.output_path,k])
        self.inputs=inputs
        with Pool() as p:
            p.map(self.parrallel_downsample,inputs)
        
        # Load in semi final image stack
        self.output_image_log=glob.glob(os.path.join(self.output_path,'*.tif*'))
        self.output_image_log=sorted(self.output_image_log,key=self.custom_sort_ds)
        self.image_stack=[]
        for image in self.output_image_log:
            image_oh=imread(image)
            self.image_stack.append(image_oh)
        
        for f in self.output_image_log:
            os.remove(f)
        
        #Downsample the z axis. 
        self.image_stack=np.array(self.image_stack)
        self.image_stack=zoom(self.image_stack,(0.08,1,1))
        
        #Write image stack to outputpath
        for i,filename in enumerate(self.output_image_log):
            imsave(os.path.join(self.output_path,f'{i}.tif'),self.image_stack[i])
            if (i+1)==self.image_stack.shape[0]:
                break
            
        return
    
parser=argparse.ArgumentParser()
parser.add_argument("--input_path",type=str,required=True)
parser.add_argument("--output_path",type=str,required=True)
parser.add_argument("--cube", type=int, nargs=6, action='append', required=True,
                    metavar=('X_START', 'X_STOP', 'Y_START', 'Y_STOP', 'Z_START', 'Z_STOP'))
   
if __name__=="__main__":
    args=parser.parse_args()
    data=generate_train_data(args.input_path,args.output_path)
    data.forward(*args.cube)
