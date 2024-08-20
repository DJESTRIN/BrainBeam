#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: DataMerger.py
Description: This script includes classes that merge multiple datasets from BrainBeam into a single tall format dataset. It utalizes the 
    Allen Reference Atlas to link cell corrdinates to brain regions and converts these counts to a final dataset.  
Author: David Estrin
Date: 2024-008-15
Version: 2.0
Usage: python DataMerger.py --input data.csv --output results.csv
"""
import json
import numpy as np 
from skimage.io import imread
import sys
from cloudreg.scripts.ARA_stuff.parse_ara import *
from BrainBeam.statistics.princeton_ara import *
from tqdm import tqdm
import pandas as pd
import re
from itertools import combinations
import pickle
import argparse
import os
import fnmatch
from datetime import datetime

class channel:
    def __init__(self, image_path, atlas_path, cell_counts_path,Tree):
        """ Build channel class """
        self.image_path=image_path #Input image path
        self.atlas_path=atlas_path #Path to converted atlas
        self.cell_counts_path=cell_counts_path #Path to cell counts as a csv
        self.Tree=Tree # A Tree derived from allen reference atlas
        self.all_children=self.Tree.get_progeny(nodename='root') # All Children for current tree

        # Null variables
        self.cage=None
        self.animal=None
        self.virus=None
        self.behavior=None
        self.cort=None
    
    def __call__(self):
        # Get information from files/paths
        self.channel = self.parse_channel(self.image_path)
        self.parse_path(self.image_path) 

        # Get cell coordinates
        self.load_cell_corrdinates()

        # Register cells to atlas
        self.basic_registration()
        
        print("Building data in tall format...")
        self.build_tall_format()
        return print(f'Finished with cage {self.cage} animal {self.animal} treatment {self.cort}')
    
    def parse_channel(self,path):
        pattern = r'Ex_(\d+)_Em_(\d+)'
        match = re.search(pattern, path)
        
        if match:
            # Extract the matched groups
            ex_value = match.group(1)
            em_value = match.group(2)
            return f"Ex_{ex_value}_Em_{em_value}"
        else:
            return None
        
    def channel_as_string(self):
        """ Returns channel name as string """
        if hasattr(self,'channel'):
            return f"{self.channel}"
        else:
            return None

    def parse_path(self,pathoh):
        """ Get vital information from file/folder names and set it to attribute"""
        keywords = ["CAGE", "ANIMAL", "VIRUS", "BEHAVIOR", "CORT"]
        pattern = r'\b(' + '|'.join(keywords) + r')\b:(\w+)'
        matches = re.findall(pattern, pathoh)
        
        # Set attributes based on the extracted information
        for key, value in matches:
            if hasattr(self, key.lower()):
                setattr(self, key.lower(), value)
        
    def load_cell_corrdinates(self):
        """ Read in csv or json files, set coordinates to attribute """
        # Parse input file path
        if 'csv' in self.cell_counts_path:
            df=pd.read_csv(self.cell_counts_path)
            self.cells=df.to_numpy()
        else:
            print('loading counts as json')
            with open(self.cell_counts_path,'r') as f:
                self.cells = json.load(f)
    
        # Eliminate double counts if present
        self.eliminate_double_counts()

        # Get total cell count
        self.total_cells=len(self.cells)

    def eliminate_double_counts(self):
        print(f'Eliminating double counts for cage {self.cage} animal {self.animal} treatment {self.cort} ')
        doubled_counts=self.cell_coexpression(self.cells, self.cells) #Find double counts via co-expression
        self.cells=np.delete(self.cells,np.where(doubled_counts==1),axis=0) # Remove double counts from data set. 
        print(f'Finished eliminating double counts for cage {self.cage} animal {self.animal} treatment {self.cort} ')
    
    def cell_coexpression(self,cell_list1,cell_list2):
        """Checks for coexpression. also used to eliminate double counts"""
        flag=np.zeros(len(cell_list1))
        index=0
        
        for c1 in tqdm(cell_list1,total=len(cell_list1)):
            for c2 in cell_list2:
                distance=np.linalg.norm(c2-c1)
                if distance<self.coexpression_threshold:
                    if distance>0:
                        flag[index]=1
            index+=1
        return flag
        
    def basic_registration(self):
        """ Registration algorithim that does not run parrallel workers """
        # Doulbe check attribute is numpy array
        self.cells=np.asarray(self.cells) 

        # Find Z-planes and images that will need to be opened
        self.cells=self.cells[self.cells[:,2].argsort()] #sort by z dimension
        images_needed=np.unique(self.cells[:,2]) #All images that will be opened
        images_needed=images_needed.astype(int)
        images_needed=np.unique(images_needed)
        
        # Empty List for registered regions
        self.cell_atlas_ids=[]
        
        #Loop through unique images
        print("Registering cells to atlas...")
        for image in tqdm(images_needed):
            #Open up image
            image_name=self.atlas_path+str(image)+".tiff"
            image_oh=np.array(imread(image_name))
            
            # Get all cells that are inside current image that is open
            cells_oh=self.cells[np.where(self.cells[:,2].astype(int)==image),:] 

            # Loop over cells and append the brain region ID to list. 
            for cell in cells_oh[0]:
                x,y,z=cell
                brain_region=image_oh[y.astype(int),x.astype(int)]
                self.cell_atlas_ids.append(brain_region)

        # Remove bad brain regions ... ?
        dt=np.dtype('float,float')
        self.cell_atlas_ids=np.array(self.cell_atlas_ids,dt)
        self.cell_atlas_ids=self.cell_atlas_ids['f1']
        self.cell_atlas_ids=self.cell_atlas_ids[~np.isnan(self.cell_atlas_ids)]
        self.cell_atlas_ids=self.cell_atlas_ids[self.cell_atlas_ids!=0]

        # Convert atlas IDs to atlas names
        self.cell_atlas_names=[]
        self.not_on_list=[]
        print('Looping over atlas IDs to convert to atlas names')
        for c in tqdm(self.cell_atlas_ids):
            try:
                self.cell_atlas_names.append(self.all_children[0][self.all_children[1].index(c)])
            except:
                self.not_on_list.append(c)
        return
            
    def build_tall_format(self):
        """ Take cdata regarding cells and put them into tall format. 
            Experiment, channel, cage, subjectid, virus, behavior, treatment, location, n
        """
        # Prepare atlas names into an array
        cell_array=np.asarray(self.cell_atlas_names)
        cell_array=cell_array.T
        cell_array=np.expand_dims(cell_array,axis=1)
        
        # Prepare mouse information into an array
        mouse_info=[self.experiment,self.channel,self.cage,self.subjectid,self.virus,self.behavior,self.treatment]
        mouse_info=np.asarray(mouse_info)
        mouse_info2=np.tile(mouse_info.T,(cell_array.shape[0],1))

        # Concat atlas and mouse data into a single dataframe
        data=np.hstack((mouse_info2,cell_array))
        df=pd.DataFrame(data,columns=['experiment','channel','cage','subjectid','virus','behavior','treatment','location'])
        
        # Create an array of ones used for aggregation
        onemat=np.ones(cell_array.shape[0])
        df['n']=onemat

        #Save to drop path, one csv file per brain
        filename=self.output_path+f"{self.channel}_tall.csv"
        df.to_csv(filename)
        return
    
class sample:
    def __init__(self):
        self.channels=[]
    
    def add_channel(self,channel_object):
        self.channels.append(channel_object)
    
    @classmethod
    def load(cls,filename):
        """Load an instance from a pickle file."""
        with open(filename, "rb") as file:
            return pickle.load(file)
    
    def save(self,filename):
        """Save the instance to a file using pickle."""
        with open(filename, "wb") as file:
            pickle.dump(self, file)

    def find_coexpression(self,obj1, obj2,threshold=20):
        """ Finds co-expression of two different channels. 
        Returns an array of ones and zeros the size of first channel indicating whether cell is co-expressed.
        Does not let cells 100% overlap. """
        # Define the action you want to perform on each pair of objects
        print(f"Finding coepxression in {obj1} and {obj2}")
        
        # Create a empty array for determining if co-expression
        flag=np.zeros(len(obj1.cells))
        index=0
        for c1 in tqdm(obj1.cells,total=len(obj1.cells)):
            for c2 in obj2.cells:
                distance=np.linalg.norm(c2-c1)
                if distance<threshold:
                    if distance>0:
                        flag[index]=1
            index+=1

        return flag

    def get_coexpression(self):
        """ Calculate the co-expression for every combination of channels """
        # Check more than one channel
        if len(self.channels) < 2:
            print("Not enough channels to find co-expressing cells")
            return
        
        # Generate combinations of 2 objects from the list
        self.comparisons=[] # Holds the names of the channels being compared
        self.coexpression=[] # Calculates actuall co-expression
        self.total_coexpression=[] # Holds total co-expressing number of cells
        self.IOU=[] #Holds intersection over union results
        for channel1, channel2 in combinations(self.channels, 2):
            # Save details to list
            self.comparisons.append([channel1.channel_as_string(),channel2.channel_as_string()])

            #Calculate coexpression
            coexpressionoh=self.find_coexpression(channel1, channel2)
            self.coexpression.append(coexpressionoh)

            # Calculate total co-expressing cells
            total_coexpressing = coexpressionoh.sum()
            self.total_coexpression.append(total_coexpressing)

            # Calculate the intersection over union of two channels
            IOU = total_coexpressing/(len(channel1.cells) + len(channel2.cells) - total_coexpressing)
            self.IOU.append(IOU)

            print(f"There were {total_coexpressing} co-expressing cells with IOU {IOU} for {channel1.channel_as_string()} and {channel2.channel_as_string()}")

class rabies_sample(sample):
    def __init__(self,output_file):
        super.__init__(self)
        self.output_file=output_file

    def label_channels(self):
        for obj in self.channels:
            # Determine which channels are helper virus or rabies virus
            if obj.channel=='Ex_647_Em_680':
                obj.rabies_channel=True
                obj.helper_channel=False
            else:
                obj.rabies_channel=False
                obj.helper_channel=True
    
    def get_coexpression(self):
        super().get_coexpression()
        for k, (channel1, channel2) in enumerate(combinations(self.channels, 2)):
            if (channel1.rabies_channel is True) and (channel2.helper_channel is True):
                print(f"The rabies channel and helper virus channel have {self.total_coexpression[k]} total overlapping cells")
            elif (channel2.rabies_channel is True) and (channel1.helper_channel is True):
                print(f"The rabies channel and helper virus channel have {self.total_coexpression[k]} total overlapping cells")

def open_ara(ara_file="/home/fs01/dje4001/CloudReg/cloudreg/scripts/ARA_stuff/ara_ontology.json"):
    with open(ara_file) as infile:
        ontology_dict = json.load(infile)
    return ontology_dict

def find_matching_subdirectories(directory, pattern):
    entries = os.listdir(directory)
    matching_dirs = [entry for entry in entries if os.path.isdir(os.path.join(directory, entry)) and fnmatch.fnmatch(entry, pattern)]
    return matching_dirs

def rabies_main():
    # Parse command line inputs
    parser = argparse.ArgumentParser(description="Get all main directories")
    parser.add_argument('--image_path', type=str, help='Path to image folder')
    parser.add_argument('--atlas_path', type=str, help='Path to atlas images')
    parser.add_argument('--cell_counts_path', type=str, help='Path to cell count file')
    parser.add_argument('--output_path', type=str, help='Path to output folder')
    args = parser.parse_args()

    # Open ontology dictonary
    ontology_dict = open_ara()
    Tree_oh = Graph(ontology_dict=ontology_dict)

    # Create sample object
    sample_oh = rabies_sample()

    # Get all channels
    channels = find_matching_subdirectories(args.image_path,'Ex_*_Em_*')
    for channel_path_oh in channels:
        # Build channel object and run 
        channel_oh = channel(channel_path_oh,args.atlas_path,args.cell_counts_path,Tree_oh)
        channel_oh()

        # Output essential dataframes

        # Add channel object to the sample object
        sample_oh.add_channel(channel_object=channel_oh) 

    # Calculate starter cells
    rabies_sample.get_coexpression()

    # Save rabies sample object for later stats
    current_datetime = datetime.now()
    formatted_datetime = current_datetime.strftime("%Y-%m-%d_%H-%M-%S")
    filenameoh=f"{args.output_path}/rabies_sample_object_{formatted_datetime}.pkl"
    rabies_sample.save(filename=filenameoh)

if __name__=='__main__':
    rabies_main()
