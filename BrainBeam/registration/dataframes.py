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
from rich.progress import Progress
from joblib import Parallel, delayed
import multiprocessing
import matplotlib.pyplot as plt

import ipdb

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

        elif 'tmt' in path_oh.lower():
            group='tmt'

        elif 'vanilla' in path_oh.lower():
            group='vanilla'

        elif 'water' in path_oh.lower():
            group='water'

        else:
            group='control'
        return cage, animal, group

    def gather_data(self):
        # Find all mapped files in final path
        mapped_files = sorted(glob.glob(os.path.join(self.data_path, "**", "*mapped*.npy"), recursive=True))
        channel_files = sorted(glob.glob(os.path.join(self.data_path, "**", "*channel_*.npy"), recursive=True))

        if len(mapped_files) != len(channel_files):
            raise ValueError(
                f"Found {len(mapped_files)} mapped arrays but {len(channel_files)} channel-name arrays in {self.data_path}."
            )

        # Load in data from files as numpy array
        # Get medidata containing animal info into list
        self.data = []
        self.medidata = []
        self.channel_data = []
        self.channel_medidata = []
        for npfile,channelfile in zip(mapped_files,channel_files):
            self.data.append(np.load(npfile))
            self.medidata.append(self.strip_file_to_name(path_oh = npfile))

            self.channel_data.append(np.load(channelfile))
            self.channel_medidata.append(self.strip_file_to_name(path_oh = channelfile))

class array_to_dataframe():
    def __init__(self, lightsheet_volume_object, tree_object, data_path):
        self.not_plotted = True
        self.data_path = data_path
        self.tree_object = tree_object
        self.lightsheet_volume_object = lightsheet_volume_object

        # Dataframe output files
        self.tall_dataframe_output_file = None
        self.wide_dataframe_output_file = None

        self.progress_bar = Progress()
        self.progress_bar.start() 

    def __call__(self):
        self.volume_to_dataframe()
        self.tall_to_wide_dataframe()
        self.progress_bar.stop() 
    
    @staticmethod
    def process_region(key, atlas, mask, tree_object):
        if key == 0:
            return None  # Skip background

        # Determine ipsi vs contra sides. For unilateral rabies injections, ipsi is assumed to be side with most labeling
        midpoint = atlas.shape[1] // 2
        left_total = mask[:, :midpoint, :].sum()
        right_total = mask[:, midpoint:, :].sum()

        if left_total >= right_total:
            ipsi_side = 'left'
        else:
            ipsi_side = 'right'

        left_indeces = np.where((atlas == key) & (np.indices(atlas.shape)[1] < midpoint))
        right_indeces = np.where((atlas == key) & (np.indices(atlas.shape)[1] > midpoint))

        if ipsi_side == 'left':
            raw_cell_count_ipsi = mask[left_indeces].sum()
            raw_cell_count_contra = mask[right_indeces].sum()
        else:
            raw_cell_count_ipsi = mask[right_indeces].sum()
            raw_cell_count_contra = mask[left_indeces].sum()

        # Normalize
        total_cells = mask.sum()
        if total_cells == 0:
            normalized_cell_count_ipsi = 0
            normalized_cell_count_contra = 0
        else:
            normalized_cell_count_ipsi = raw_cell_count_ipsi / total_cells
            normalized_cell_count_contra = raw_cell_count_contra / total_cells

        # Get region name from id
        node_oh = tree_object.find_node(id_or_name=int(key))
        region_name = node_oh["name"]

        return [region_name, key, raw_cell_count_ipsi, normalized_cell_count_ipsi], \
            [region_name, key, raw_cell_count_contra, normalized_cell_count_contra]

    def atlas_to_counts(self, atlas, mask):
        keys = np.unique(atlas)

        results = Parallel(n_jobs=-1, backend="loky")(delayed(self.process_region)(key, atlas, mask, self.tree_object) for key in keys)

        results = [r for r in results if r is not None]
        if not results:
            empty = np.empty((0, 4), dtype=object)
            return empty, empty

        ipsi_key_and_counts, contra_key_and_counts = zip(*results)

        return np.array(ipsi_key_and_counts), np.array(contra_key_and_counts)

    def plot_midline(self,atlas,mask):
        if self.not_plotted:
            # Choose a slice index to visualize
            slice_idx = atlas.shape[0] // 2  # middle slice in Z

            # Midline
            midpoint = atlas.shape[1] // 2

            fig, axs = plt.subplots(1, 2, figsize=(12, 6))

            # Plot atlas in grey: 0 -> black, anything else -> white
            atlas_slice = atlas[slice_idx]
            atlas_display = np.where(atlas_slice > 0, 1.0, 0.0)  # 1 for regions, 0 for background

            axs[0].imshow(atlas_display, cmap='gray')
            axs[0].axhline(midpoint, color='red', linestyle='--', label='Midline')
            axs[0].set_title('Atlas (grey)')
            axs[0].legend()

            # Plot mask
            axs[1].imshow(mask[slice_idx], cmap='gray')
            axs[1].axhline(midpoint, color='red', linestyle='--', label='Midline')
            axs[1].set_title('Mask')
            axs[1].legend()

            for ax in axs:
                ax.axis('off')

            plt.tight_layout()
            plt.savefig('atlasmidline.jpg')

            self.not_plotted=False

    def volume_to_dataframe(self):
        """ Convert numpy arrays into dataframes """
        data = self.lightsheet_volume_object.data
        medidata = self.lightsheet_volume_object.medidata

        # Go through each key in the atlas and get total cell counts
        self.df = pd.DataFrame(columns=['subject', 'cage', 'suid', 'group', 'channel',
                                    'lateralization', 'regionname', 'regionid', 
                                    'rawcount', 'normalizedcount'])

        self.subject_progress_bar = self.progress_bar.add_task("[cyan]Subject...", total=len(data))
        self.count_progress_bar = self.progress_bar.add_task("[magenta]Cell Count channels ...", total=1)  # Placeholder total

        for it, (data_oh, medidata_oh) in enumerate(zip(data,medidata)):
            # Parse current data
            id_atlas = data_oh[:,:,:,0]
            template_atlas = data_oh[:,:,:,1]
            moving_image = data_oh[:,:,:,2]
            aggregate_cell_counts = data_oh[:,:,:,3:]
            cage, animal, group = medidata_oh
            
            # Create count progress bar
            self.progress_bar.reset(self.count_progress_bar, total=aggregate_cell_counts.shape[3])
            for k,channel_name in zip(range(aggregate_cell_counts.shape[3]),self.lightsheet_volume_object.channel_data[it]):
                channel_name_oh = channel_name
                mask_oh = aggregate_cell_counts[:,:,:,k]

                self.plot_midline(atlas=id_atlas,mask=mask_oh)

                # Generate an array containing RegionName, RegiodID, Lateralization, Rawcount and NormalizedCount
                key_to_counts_oh_ipsi, key_to_counts_oh_contra  = self.atlas_to_counts(atlas=id_atlas,mask=mask_oh)
                
                # Use numpy tile to repeate important information
                subject_column = np.tile(animal, len(key_to_counts_oh_ipsi))
                cage_column = np.tile(cage, len(key_to_counts_oh_ipsi))
                suid_column = np.tile(f'{cage}_{animal}', len(key_to_counts_oh_ipsi))
                group_column = np.tile(group, len(key_to_counts_oh_ipsi))
                channel_column = np.tile(f'{channel_name_oh}', len(key_to_counts_oh_ipsi))
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

                # Update progress bar
                self.progress_bar.update(self.count_progress_bar, advance=1)

            # Update progress bar
            self.progress_bar.update(self.subject_progress_bar, advance=1)

        self.df.to_csv(os.path.join(self.data_path,"df_tall.csv"),index=False)
    
    def tall_to_wide_dataframe(self):
        self.df_wide = self.df.pivot(index=['suid','channel','lateralization'], columns='regionname', values=['rawcount', 'normalizedcount'])
        self.df_wide.columns = ['_'.join(col).strip() for col in self.df_wide.columns.values]
        self.df_wide = self.df_wide.reset_index()
        self.df_wide.to_csv(os.path.join(self.data_path,"df_wide.csv"),index=False)

if __name__=='__main__':
    multiprocessing.set_start_method("spawn", force=True)

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
