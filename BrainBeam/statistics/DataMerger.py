import json
import numpy as np 
from skimage.io import imread
import sys
sys.path.insert(0,'/home/fs01/dje4001/CloudReg/')
sys.path.insert(0,'/home/fs01/dje4001/lightsheet_cluster/')
from cloudreg.scripts.ARA_stuff.parse_ara import *
from princeton_ara import *
import argparse
import itertools
from tqdm import tqdm
import ipdb
from multiprocessing import Pool
import ipdb
import pandas as pd
import re

# Generate a tree strucutre from Allen Registered Atlas file. Used for parsing
ara_file="/home/fs01/dje4001/CloudReg/cloudreg/scripts/ARA_stuff/ara_ontology.json"
with open(atlas_json_file,'r') as infile:
    ontology_dict = json.load(infile)

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
        self.parse_path() 

        # Get cell coordinates
        self.load_cell_corrdinates()

        # Register cells to atlas
        self.basic_registration()
        
        print("Building data in tall format...")
        self.build_tall_format()
        return print(f'Finished with cage {self.cage} animal {self.animal} treatment {self.cort}')
    
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
            
    def level_registration(self,level):
        """ Takes the registration list, and converts it to different level 
            Example: converting crebellar cortex, purkinje layer to cerebellum
            input and output should be a column that is the same size"""
        #Separate ara into groups by level, get names of children
        names,__=get_children_names(self.ara_file,level)
        
        #Generate new list of names where new names must be member of level.
        cell_atlas_names_leveled=self.cell_atlas_names[:]
        for i,current_name in enumerate(self.cell_atlas_names):
            Found=False
            for key in names:
                for child in names[key]:
                    if current_name == child:
                        cell_atlas_names_leveled[i]=key
                        Found=True
                        break
                if Found==True:
                    break
            if Found==False:
                cell_atlas_names_leveled[i]=current_name
        return cell_atlas_names_leveled
    
    def move_up_tree(self,steps):
        #Generate new list of names where new names must be member of level.
        self.cell_atlas_names_step=[]
        index=[]
        for current_name in self.cell_atlas_names:
            if steps>1:
                for u in range(steps):
                    try:
                        current_name=Tree.get_parent(current_name)
                    except:
                        if current_name==None:
                            break
                self.cell_atlas_names_step.append(current_name)
            elif steps<1:
                print("steps for move_up_tree method is incorrect, please fix")
                return self.cell_atlas_names_step
            else:
                self.cell_atlas_names_step.append(Tree.get_parent(current_name))
        return self.cell_atlas_names_step
    


    def build_tall_format(self):
        """ Take cdata regarding cells and put them into tall format. 
        
            cage, subjectid, virus, behavior, treatment, channel,number_of_cell_index,
            brain_region_lf,l2,l3,l4,l5,l6, etc.
        """
        cell_array=np.asarray(self.cell_atlas_names)
        level_array=np.asarray(self.levels)
        cell_array=cell_array.T
        cell_array=np.expand_dims(cell_array,axis=1)
        level_array=level_array.T
        onemat=np.ones(cell_array.shape[0])
        
        
        mouse_info=[self.experiment,self.channel_name,self.cage,self.subjectid,self.virus,self.behavior,self.treatment]
        mouse_info=np.asarray(mouse_info)
        mouse_info2=np.tile(mouse_info.T,(cell_array.shape[0],1))
        data=np.hstack((mouse_info2,cell_array,level_array))

        df=pd.DataFrame(data,columns=['experiment','channel','cage','subjectid','virus','behavior','treatment','location','lv1','lv2','lv3','lv4','lv5','lv6','lv7','lv8','lv9','lv10'])
        df['n']=onemat
        filename=self.output_path+"tall.csv"
        df.to_csv(filename)
        #Save to drop path, one csv file per brain
        return