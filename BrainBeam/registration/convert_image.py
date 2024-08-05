#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" Image Sequence conversions """
#Load packages
import SimpleITK as sitk 
import numpy as np
import cv2
from scipy.ndimage import zoom
import argparse
import glob
import os
import re
import warnings
from multiprocessing import Pool
from skimage.io import imread, imsave
import ipdb

class resample_images(object):
    """ class which can up or downsample a sequence of tiff images.
        Currently only resamples the x and y axis, not the z axis"""
    def __init__(self,input_path,output_path,target_image_size,mode):
        self.input_path=input_path
        self.output_path=output_path
        self.mode=mode 
        self.target_image_size=target_image_size
        
        if self.mode != 'constant' or self.mode != 'nearest':
            warnings.warn("Suggested setting for mode are 'constant' or 'nearest'. See scipy.ndimage.zoom for all choises for mode")
        
        try:
            #Get tiff images in input directory
            os.chdir(self.input_path)
            self.image_log=glob.glob('*.tif*')
            self.image_log=sorted(self.image_log,key=self.custom_sort)
            
            #Get image shape from first image, find factor to resize x and y
            example_image=np.array(imread(self.image_log[0]))
        except:
            print("No tiff images for this file")
            tmp=sitk.ReadImage(self.input_path)
            img=sitk.GetArrayFromImage(tmp)
            img=np.asarray(img,dtype='uint64')
            for image in img:
                example_image=image
                break
            
        self.x_change,self.y_change=self.target_image_size[0]/example_image.shape[0],self.target_image_size[1]/example_image.shape[1]
        
    def custom_sort(self,x):
        """ Sort function might need to be changed depending on how images are named """
        return int(re.sub(r'[^0-9]','',(os.path.basename(x))))
    
    def resample_image(self):
        """ resample sequence of tiff images """
        # Place all inputs into a list
        inputs=[]
        for k,filename in enumerate(self.image_log):
            inputs.append([filename,self.output_path,self.x_change,self.y_change,k,self.mode])
        
        #Resampling can be slow. To speed up, images are run in parrallel. 
        with Pool() as p:
            p.map(self.parrallel_resample,inputs)
        
    def parrallel_resample(self,x):
        """input x contains a list of  """
        #Parse the input x
        image_path=x[0]
        image_output_path=x[1]
        x_change=x[2]
        y_change=x[3]
        z=x[4]
        mode_oh=x[5]
        
        #Read image and resample
        image_oh=np.array(imread(image_path))
        #rs_image_oh=zoom(image_oh,(x_change, y_change),mode=mode_oh)
        #image_oh=cv2.imread(image_path)
        rs_image_oh=cv2.resize(image_oh,(self.target_image_size[0],self.target_image_size[1]),interpolation=cv2.INTER_NEAREST)
        string_name=image_output_path+str(z)+".tiff"
        cv2.imwrite(string_name,rs_image_oh)
        return

class convert_img_to_tiff(resample_images):
    """ Convert img file to tiff sequence then resize it to size of choice """
    def forward(self):
        self.convert()
        self.input_path=self.output_path
        
        #Get tiff images in input directory
        os.chdir(self.input_path)
        self.image_log=glob.glob('*.tif*')
        self.image_log=sorted(self.image_log,key=self.custom_sort)
        
        #Run resampling
        self.resample_image()
    
    def convert(self):
        # Convert to numpy array
        tmp=sitk.ReadImage(self.input_path)
        img=sitk.GetArrayFromImage(tmp)
        img=np.asarray(img,dtype='uint64') 
        
        #Loop through array and save as tiff sequence.
        counter=0
        for image in img:
            string_name=self.output_path+str(counter)+".tiff"
            cv2.imwrite(string_name,image)
            counter+=1
        return
    
if __name__=='__main__':
  # Command line interface
  parser = argparse.ArgumentParser(description="Convert image (atlas) to image sequence")
  parser.add_argument("--input_image_path", type=str, help="The directory containing the input TIFF stack or path to IMG file.",required=True)
  parser.add_argument("--output_path", type=str, help="The directory to save the output TIFF stack.",required=True)
  parser.add_argument("--target_image_sizex",type=int,help="final image size: x axis",required=True)
  parser.add_argument("--target_image_sizey",type=int,help="final image size: y axis",required=True)
  parser.add_argument("--mode",type=str,default='constant',help="scipy.ndimage.zoom's mode of interpolation",required=True)
  args = parser.parse_args()

  #Start resampling (and conversion if .img is input)
  if ('.img' in args.input_image_path):
      data=convert_img_to_tiff(args.input_image_path, args.output_path,(args.target_image_sizex,args.target_image_sizey),args.mode)
      data.forward()
  else:
      resample_images(args.input_image_path, args.output_path,args.target_image_size,args.mode)
  
# """ Testing """
# input_image_path="/athena/listonlab/scratch/dje4001/rabies_cort_experimental/lightsheet/registered/20220925_12_49_48_CAGE3752774_ANIMAL04_VIRUSRABIES_CORTEXPERIMENTAL/20220925_12_49_48_CAGE3752774_ANIMAL04_VIRUSRABIES_CORTEXPERIMENTAL_Ex_647_Em_680_registration/downloop_1_labels_to_target_highres.img"
# output_path="/athena/listonlab/scratch/dje4001/rabies_cort_experimental/lightsheet/registered/20220925_12_49_48_CAGE3752774_ANIMAL04_VIRUSRABIES_CORTEXPERIMENTAL/tiffsequence/"
# target_image_sizex=7422
# target_image_sizey=7367
# mode="nearest"
# data=convert_img_to_tiff(input_image_path,output_path,(target_image_sizex,target_image_sizey),mode)
# data.forward()
  

  
    
  
    
  
    
  
    
  
    
  
    
  
