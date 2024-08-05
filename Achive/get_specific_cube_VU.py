#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" Downsample Image Stack """
from skimage.io import imread, imsave
from scipy.ndimage import zoom
import numpy as np
import glob
import os
import re
from multiprocessing.pool import ThreadPool as Pool
import warnings
import random
import argparse
warnings.filterwarnings("ignore")
import ipdb

class generate_train_data(object):
    def __init__(self, input_path, output_path,*args):
        #input path contains all channels for a single sample
        #output path should be a folder in storage. 
        self.input_path=input_path
        self.output_path=output_path
        
        #Get image list
        os.chdir(self.input_path)
        self.image_log=glob.glob('*.tif*')
        self.image_log=sorted(self.image_log,key=self.custom_sort)
        
        
        #Get image properties
        image_oh=imread(self.image_log[0])
        (self.x,self.y)=image_oh.shape
        self.z=len(self.image_log)

        
    def forward(self,*args):
        if not args:
            self.get_cubes()
        else:
            self.get_cubes(list(args))
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
            cubes=[]
            for u in range(0,len(args)):
                cube_oh=args[u]
                cubes.append(cube_oh)
              
            self.cubes=list(cubes)
            self.cubes=list(self.cubes[0][0])
            print(self.cubes)
        return
    
    def make_output_dirs(self):
        #Generates a new path for each cube
        for u in range(15):
            output_sub=self.output_path+str(u)+"/"
            if not os.path.exists(output_sub):
                os.mkdir(output_sub)
        
    def custom_sort(self,x):
        return int(re.sub(r'[^0-9]','',(os.path.basename(x))))

    def parallel_crop(self,x):
        filename=x[0]
        cube=x[1]
        output_num=x[2][0]
        output_path=self.output_path+str(output_num)+"/"
        image_oh=imread(filename)
        crop_image_oh=image_oh[cube[0]:cube[1],cube[2]:cube[3]]
        imsave(output_path+filename,crop_image_oh)
        return

    def grab_cube(self):
        self.cubes=np.array(self.cubes)
        self.cubes=np.atleast_2d(self.cubes)
        allinputs=[]
        for i,cube in enumerate(self.cubes):
            #Loop through images on z stack
            self.image_log_oh=self.image_log[cube[4]:cube[5]]
            cube_repeated=np.tile(np.array(cube),(cube[5]-cube[4],1))
            cube_repeated=cube_repeated.tolist()
            
            output_repeated=np.tile(np.array(i),(cube[5]-cube[4],1))
            output_repeated=output_repeated.tolist()

            inputs=list(zip(self.image_log_oh,cube_repeated,output_repeated))
            allinputs.append(inputs)
        
        inputs=[item for sublist in allinputs for item in sublist]
            
        with Pool() as p:
            p.map(self.parallel_crop,inputs)
                
        return
    
    def parrallel_downsample(self,x):
        filename=x[0]
        output_path=x[1]
        image_oh=np.array(imread(filename))
        ds_image_oh=zoom(image_oh,(0.08,0.08))
        imsave(output_path+str(x[2])+".tif",ds_image_oh)
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
        os.chdir(self.output_path)
        self.output_image_log=glob.glob('*.tif*')
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
            imsave(self.output_path+str(i)+'.tif',self.image_stack[i])
            if (i+1)==self.image_stack.shape[0]:
                break
            
        return
    
    
if __name__=="__main__":
    input_path='/athena/listonlab/scratch/dje4001/rabies_cort_experimental/lightsheet/stitched/20220926_17_49_34_CAGE4094795_ANIMAL01_VIRUSRABIES_CORTEXPERIMENTAL/Ex_647_Em_680/'
    output_path='/athena/listonlab/scratch/dje4001/rabies_cort_experimental/lightsheet/training_data/20220926_17_49_34_CAGE4094795_ANIMAL01_VIRUSRABIES_CORTEXPERIMENTAL/'
    ### Double check x and y is correct. ImageJ x equals this script's y.
    data=generate_train_data(input_path,output_path,[[6000,6500,4000,4500,1000,1500],
                                                     [4300,4800,4500,5000,1000,1500],
                                                     [4100,4600,1620,2120,1020,1520],
                                                     [1730,2230,4012,4512,1020,1520],
                                                     [3420,3920,5600,6100,1500,2000],
                                                     [7700,8200,4000,4500,1520,2020],
                                                     [300,800,1000,1500,1520,2020],
                                                     [4300,4800,3400,3900,2040,2540],
                                                     [1700,2200,3000,3500,2040,2540],
                                                     [7200,7700,3400,3900,2040,2540],
                                                     [6800,7300,5000,5500,2550,3050],
                                                     [7200,7700,3000,3500,2550,3050],
                                                     [3800,4300,3500,4000,2550,3050],
                                                     [2000,2500,3400,3900,2550,3050]
                                                     ])
    data.forward([[6000,6500,4000,4500,1000,1500],
                    [4300,4800,4500,5000,1000,1500],
                    [4100,4600,1620,2120,1020,1520],
                    [1730,2230,4012,4512,1020,1520],
                    [3420,3920,5600,6100,1500,2000],
                    [7700,8200,4000,4500,1520,2020],
                    [300,800,1000,1500,1520,2020],
                    [4300,4800,3400,3900,2040,2540],
                    [1700,2200,3000,3500,2040,2540],
                    [7200,7700,3400,3900,2040,2540],
                    [6800,7300,5000,5500,2550,3050],
                    [7200,7700,3000,3500,2550,3050],
                    [3800,4300,3500,4000,2550,3050],
                    [2000,2500,3400,3900,2550,3050]])


# parser=argparse.ArgumentParser()
# parser.add_argument("--input_path",type=str,required=True)
# parser.add_argument("--output_path",type=str,required=True)
   
# if __name__=="__main__":
#     args=parser.parse_args()
#     generate_train_data(args.input_path,args.output_path)
   # thresh2 = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    #                                      cv2.THRESH_BINARY, 199, 5)
