#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mass Univariate T-tests
to atlas
"""
import pandas as pd
import numpy as np
from skimage.io import imread, imsave
import matplotlib.pyplot as plt
from scipy import stats
from princeton_ara import Graph
import json
import os
import ipdb
import warnings
warnings.simplefilter('ignore')

### TO DO
# Does code currently take into account child structures when plotting?

class inject_atlas():
    def __init__(self,atlas_json_file=[],atlas_path=[],drop_directory=[]):
        self.atlas_path=atlas_path
        self.drop_directory=drop_directory

        #Set up ARA tree
        with open(atlas_json_file,'r') as infile:
            ontology_dict = json.load(infile)
        self.tree=Graph(ontology_dict)
    
    def __call__(self,):
        self.get_atlas_stack()

    def get_atlas_stack(self):
        self.atlas_stack=imread(self.atlas_path)
        self.atlas_stack=np.squeeze(np.array(self.atlas_stack))
        self.atlas_stack=self.atlas_stack.astype('float')
        return

    def regions_to_ids(self,brainregions):
        """ Searches for brainregions in ARA tree and finds corresponding ID """
        ids=[]
        for region in brainregions:
            ids.append(self.tree.get_id(region))
        self.ids=np.array(ids)

    def inject_data_to_stack(self,data,skip_frames=50,mode='continuous',threshold=0.05):
        """ Take data of interest and inject it into the ARA stack """
        injected_slices=[] # Final list of colored slices
        for sn in range(1,self.atlas_stack.shape[2]):
            if (sn%skip_frames)==0:
                # Get current slice from stack
                slicea=self.atlas_stack[:,:,sn]

                # Set background of image to nan
                background=stats.mode(slicea) 
                background=background[0][0][0]
                slicea[np.where(slicea==background)]=np.nan  

                #Copy current slice as the final output slice      
                slicec=np.copy(slicea) 

                # Switch Case --- mode must match one of three categories
                # continous is for data such as t-values where you want to see range
                # binary is for data with a cut off. Ex. pvalue<0.05
                # Reference is a special case where reference atlas is plotted. 
                if mode=='continuous':
                    # Loop through unique IDS in slicea and see where there is overlap
                    for i in np.unique(slicea):
                        value=data[np.where(self.ids==i)]
                        slicec[np.where(slicea==i)]=value

                elif mode=='binary':
                    for i in np.unique(slicea):
                        value=data[np.where(self.ids==i)]
                        if value<threshold:
                            new_value=200
                        else:
                            new_value=50
                        slicec[np.where(slicea==i)]=new_value

                elif mode=='reference':
                    counter=1
                    for i in np.unique(slicea):
                        slicec[np.where(slicea==i)]=counter
                        counter+=1.100000000000000123

                else:
                    raise Exception("Mode does not match continous, binary or reference formats. Please check mode setting")
                
                #Append the colored in slice to list of slices
                injected_slices.append(slicec)
        
        return injected_slices

    def plot_atlas(stack,colormap='gray'):
        ipdb.set_trace()

class mass_ttest(inject_atlas):
    def __init__(self,atlas_json_file,atlas_path,drop_directory,dataframe_path):
        super().__init__(atlas_json_file,atlas_path,drop_directory)
        self.dataframe=pd.read_csv(dataframe_path)

    def get_normalized_n(self):
        """ Normalize each cell count by the total number of cells in each sample """
        self.dataframe['normalized_n']=self.dataframe['n']
        self.dataframe['normalized_n'] = self.dataframe['n'].div(self.dataframe.groupby(['cage','subjectid'])['n'].transform('sum'))

    def __call__(self):
        """ Loop over levels and perform mass univariate t-tests """
        super().__call__()
        self.get_normalized_n()

        levels=['location', 'lv1', 'lv2', 'lv3', 'lv4', 'lv5','lv6', 'lv7', 'lv8', 'lv9', 'lv10']
        for level in levels:
            brainregions,arranged_data = self.arrange_data(level)
            print(f'There were {len(brainregions[arranged_data[:,1]<0.05])} significant regions for level {level} using raw counts')
            self.regions_to_ids(brainregions)
            stackoh=self.inject_data_to_stack(arranged_data[:,0])
            self.plot_atlas(stackoh)

            brainregions,arranged_data = self.arrange_data(level,counttype='normalized_n')
            print(f'There were {len(brainregions[arranged_data[:,1]<0.05])} significant regions for level {level} using normalized counts')

    def arrange_data(self,level_name,counttype='n'):
        # Parse data into data only necessary for running t test
        local_df = self.dataframe.groupby(['cage', 'subjectid','treatment', level_name], as_index=False)[counttype].sum()
        local_np = local_df.to_numpy()
        colnum=local_df.columns.get_loc(level_name)
        brainregions=np.unique(local_np[:,colnum])

        arranged_data=[]
        for region in brainregions:
            regiondf=local_df.loc[local_df [level_name] == region]
            dfg = regiondf.groupby('treatment')
            if dfg.ngroups>1:
                get_values=[]
                for group_name, df_group in dfg:
                    get_values.append(df_group[counttype].to_numpy())
                t_stat,p_value=self.ttest(get_values[0],get_values[1])

                # Prevent infinity error
                if t_stat==float("inf"):
                    t_stat=1
                elif t_stat==float("-inf"):
                    t_stat=-1

                arranged_data.append([t_stat,p_value])
            else:
                arranged_data.append([np.nan,np.nan])

        # Convert back to numpy array
        arranged_data=np.asarray(arranged_data)
        return brainregions,arranged_data

    def ttest(self,group1,group2):
        """ Run univariate t-test """
        return stats.ttest_ind(group1, group2) # returns t_stat and p_value


if __name__=='__main__':
    oboh=mass_ttest(atlas_json_file = '/home/fs01/dje4001/CloudReg/cloudreg/scripts/ARA_stuff/ara_ontology.json',
                    atlas_path="/home/fs01/dje4001/CloudReg/cloudreg/registration/atlases/ara_annotation_10um.tif",
                    drop_directory="/athena/listonlab/scratch/dje4001/lightsheet_scratch/rabies_cort_cohort2_figures/",
                    dataframe_path="/athena/listonlab/scratch/dje4001/lightsheet_scratch/rabies_cort_cohort2_dataset.csv")
    oboh()