#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: dataframes.py
Description: From registration output, convert data into a tall formatted dataframe  
Author: David Estrin
Date: 2024-008-15
Version: 2.0
Usage: python DataMerger.py --input data.csv --output results.csv
"""
import json
import numpy as np 
from BrainBeam.registration.atlastree import atlastree
import pandas as pd
import tqdm
import argparse
import os, glob

class lightsheet_volume_data():
    """ Get medi data regarding subject's name, group etc from path"""
    def __init__(self,data_path, voxelsize=50):
        self.data_path = data_path
        self.voxelsize = voxelsize
        self.gather_data() # Get primary data 

    def strip_file_to_name(self,path_oh):
        # Get cage id number
        _,cage = path_oh.lower().split('cage')
        cage = cage.split('_')[0]

        # Get animal id number
        _, animal = path_oh.lower().split('animal')
        animal = animal.split('_')[0]

        # Get group id
        if 'cort' in path_oh.lower():
            group='cort'
        else:
            group='control'
        return cage, animal, group

    def gather_data(self):
        # Find all mapped files in final path
        mapped_files = glob.glob(os.path.join(self.data_path,r"**\*mapped*.npy"), recursive=True)

        # Load in data from files as numpy array
        # Get medidata containing animal info into list
        self.data = []
        self.medidata = []
        for npfile in mapped_files:
            self.data.append(np.load(npfile))
            self.medidata.append(self.strip_file_to_name(path_oh = npfile))

class array_to_dataframe():
    def __init__(self, lightsheet_volume_object, tree_object, data_path):
        self.data_path = data_path
        self.tree_object = tree_object
        self.lightsheet_volume_object = lightsheet_volume_object

        # Dataframe output files
        self.tall_dataframe_output_file = None
        self.wide_dataframe_output_file = None

    def __call__(self):
        self.volume_to_dataframe()
        self.tall_to_wide_dataframe()
    
    def atlas_to_counts(self,atlas,mask):
        # Loop over atlas keys to get 
        # (1) cell counts, (2) normalized cell counts, (3) starter cell normalized cell count
        
        ipsi_key_and_counts = []
        contra_key_and_counts = []
        for key in np.unique(atlas):
            # Skip background
            if key == 0 :
                continue

            # Get all types of counts divided into ipsi and contralateral
            ipsi_indeces = np.where((atlas == key) & (np.indices(atlas.shape)[1] > (atlas.shape[1] // 2)))
            contra_indeces = np.where((atlas == key) & (np.indices(atlas.shape)[1] < (atlas.shape[1] // 2)))

            raw_cell_count_ipsi = mask[ipsi_indeces].sum()
            raw_cell_count_contra = mask[contra_indeces].sum()
    
            normalized_cell_count_ipsi = mask[ipsi_indeces].sum() / mask.sum()
            normalized_cell_count_contra = mask[contra_indeces].sum() / mask.sum()

            # Get region name from id
            node_oh = self.tree_object.find_node(id_or_name=int(key))
            region_name = node_oh["name"]

            ipsi_key_and_counts.append([region_name,key,raw_cell_count_ipsi,normalized_cell_count_ipsi])
            contra_key_and_counts.append([region_name,key,raw_cell_count_contra,normalized_cell_count_contra])
        
        ipsi_key_and_counts = np.array(ipsi_key_and_counts)
        contra_key_and_counts = np.array(contra_key_and_counts)
        return ipsi_key_and_counts, contra_key_and_counts

    def volume_to_dataframe(self):
        """ Convert numpy arrays into dataframes """
        data = self.lightsheet_volume_object.data
        medidata = self.lightsheet_volume_object.medidata

        # Go through each key in the atlas and get total cell counts
        self.df = pd.DataFrame(columns=['subject', 'cage', 'suid', 'group', 'channel',
                                    'lateralization', 'regionname', 'regionid', 
                                    'rawcount', 'normalizedcount'])

        for data_oh, medidata_oh in zip(data,medidata):
            # Parse current data
            id_atlas = data_oh[:,:,:,0]
            template_atlas = data_oh[:,:,:,1]
            moving_image = data_oh[:,:,:,2]
            aggregate_cell_counts = data_oh[:,:,:,3:]
            cage, animal, group = medidata_oh
            
            for k in tqdm.tqdm(range(aggregate_cell_counts.shape[3])):
                mask_oh = aggregate_cell_counts[:,:,:,k]

                # Generate an array containing RegionName, RegiodID, Lateralization, Rawcount and NormalizedCount
                key_to_counts_oh_ipsi, key_to_counts_oh_contra  = self.atlas_to_counts(atlas=id_atlas,mask=mask_oh)
                
                # Use numpy tile to repeate important information
                subject_column = np.tile(animal, len(key_to_counts_oh_ipsi))
                cage_column = np.tile(cage, len(key_to_counts_oh_ipsi))
                suid_column = np.tile(f'{cage}_{animal}', len(key_to_counts_oh_ipsi))
                group_column = np.tile(group, len(key_to_counts_oh_ipsi))
                channel_column = np.tile(f'channel{k}', len(key_to_counts_oh_ipsi))
                lateralization_column = np.tile(f'ipsilateral', len(key_to_counts_oh_ipsi))

                ispi_df = pd.DataFrame({'subject': subject_column, 'cage': cage_column, 'suid': suid_column, 
                                        'group': group_column,'channel': channel_column, 'lateralization': lateralization_column, 
                                        'regionname': key_to_counts_oh_ipsi[:,0], 'regionid': key_to_counts_oh_ipsi[:,1] ,
                                        'rawcount': key_to_counts_oh_ipsi[:,2], 
                                        'normalizedcount': key_to_counts_oh_ipsi[:,3]})

                lateralization_column = np.tile(f'contralateral', len(key_to_counts_oh_contra))
                contra_df = pd.DataFrame({'subject': subject_column, 'cage': cage_column, 'suid': suid_column, 
                                        'group': group_column,'channel': channel_column, 'lateralization': lateralization_column, 
                                        'regionname': key_to_counts_oh_contra[:,0], 'regionid': key_to_counts_oh_contra[:,1] ,
                                        'rawcount': key_to_counts_oh_contra[:,2], 
                                        'normalizedcount': key_to_counts_oh_contra[:,3]})

                # Append using concat (avoids performance warnings in newer pandas versions)
                df_oh = pd.concat([ispi_df, contra_df], ignore_index=True)
                self.df = pd.concat([self.df, df_oh], ignore_index=True)

        self.df.to_csv(os.path.join(self.data_path,"df_tall.csv"),index=False)
    
    def tall_to_wide_dataframe(self):
        self.df_wide = self.df.pivot(index=['suid','channel','lateralization'], columns='regionname', values=['rawcount', 'normalizedcount'])
        self.df_wide.columns = ['_'.join(col).strip() for col in self.df_wide.columns.values]
        self.df_wide = self.df_wide.reset_index()
        self.df_wide.to_csv(os.path.join(self.data_path,"df_wide.csv"),index=False)

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data_path',type=str, help="Full path containing 4D numpy file")
    args = parser.parse_args()

    # Get atlas tree data
    drop_atlas_path = os.path.join(args.data_path,"communal_atlas_drop/")

    atlas_json_file = os.path.join(drop_atlas_path,'structures.json')
    with open(atlas_json_file,'r') as infile:
        ontology_dict = json.load(infile)

    ontology_dict_oh = {i: v for i, v in enumerate(ontology_dict)}
    tree_obj = atlastree(data = ontology_dict_oh) # Build tree

    # Get medi data for current subject
    medobj = lightsheet_volume_data(data_path = args.data_path)

    # Create and output tall formatted data frame
    DFobj = array_to_dataframe(lightsheet_volume_object = medobj, tree_object = tree_obj, data_path = args.data_path)
    DFobj()
