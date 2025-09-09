#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: AtlasOperations.py
Description: 
Author: David Estrin
Date: 2025-04-09
Version: 1.0
Usage: 
"""
import os
import json
from BrainBeam.registration.atlastree import atlastree
import re
import nrrd
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import ipdb


class AtlasGardener:
    """ AtlasGardener
    This class is meant to take both atlases and ontology dictionaries and prune/preen them.
    Ontology dictinoaries from ARA are good but often do not fully correspond with given atlas. This class contains methods which
    prune unused regions from the dictionary. Also, this class contains methods which can set brain regions to a specific level.

    Inputs:
        ontology_dict (dict) -- The original ontology dictionary from ARA
        annotation_path (str) -- Path to nrrd file from ARA that is the atlas image volume.

    """
    def __init__(self, ontology_dict, drop_directory, level=6,
                 annotation_path=r'C:\Users\listo\communal_registration_logcal_drop\rabies_experiment\experimental\communal_atlas_drop\annotation\ccf_2017\annotation_50.nrrd'):
        self.atlas, _ = nrrd.read(annotation_path)
        self.drop_directory = drop_directory
        self.level = level
        self.ontology_dict = ontology_dict

    def __call__(self):
        # Remove regions from ontology not in atlas, get leaves and internal targets
        self.pruned_ontology = self.prune_ontology_list(ontology=self.ontology_dict,target_keys=np.unique(self.atlas))
        self.leaves = self.get_leaf_nodes(ontology=self.pruned_ontology)
        self.internaltargets = self.find_internal_targets(ontology=self.ontology_dict,target_keys=np.unique(self.atlas))

        # Create course dictionary based on level number. Generate map of coarsened atlas and plot.
        self.course_dict = self.coarsen_to_level(ontology=self.ontology_dict,target_keys=np.unique(self.atlas),level=self.level)
        self.coarsened_atlas = self.remap_volume(self.atlas, self.course_dict)
        self.plot_slice_grid(volume=self.coarsened_atlas) 

    def prune_ontology_list(self, ontology, target_keys):
        target_keys = set(target_keys)
        relevant_ids = set()
        for region in ontology:
            if region["id"] in target_keys:
                relevant_ids.update(region["structure_id_path"])
        return [region for region in ontology if region["id"] in relevant_ids]

    def get_leaf_nodes(self, ontology):
        all_ids = set()
        parent_ids = set()
        for region in ontology:
            sid_path = region["structure_id_path"]
            all_ids.add(region["id"])
            parent_ids.update(sid_path[:-1])
        leaf_ids = all_ids - parent_ids

        return {region["id"]: region["name"] for region in ontology if region["id"] in leaf_ids}

    def find_internal_targets(self, ontology, target_keys):
        parent_ids = set()
        for region in ontology:
            parent_ids.update(region["structure_id_path"][:-1])
        return set(target_keys) & parent_ids

    def coarsen_to_level(self, ontology, target_keys, level):
        id_to_region = {r["id"]: r for r in ontology}
        new_mapping = {}
        for key in target_keys:
            region = id_to_region.get(key)
            if not region:
                continue
            sid_path = region["structure_id_path"]
            if len(sid_path) > level:
                ancestor_id = sid_path[level]
            else:
                ancestor_id = sid_path[-1]
            ancestor = id_to_region.get(ancestor_id)
            new_mapping[key] = (ancestor_id, ancestor["name"] if ancestor else "Unknown")
        return new_mapping

    def remap_volume(self, volume, new_mapping):
        id_remap = {old: new_id for old, (new_id, _) in new_mapping.items()}
        remapped = np.copy(volume)
        unique_ids = np.unique(volume)
        for old_id in unique_ids:
            if old_id in id_remap:
                remapped[volume == old_id] = id_remap[old_id]
            else:
                remapped[volume == old_id] = old_id  
        return remapped

    def plot_slice_grid(self, volume, axis=0, num_rows=5, num_cols=5, cmap='tab20', save_path='atlasslices.jpg'):
        # Remap volume values to [0, N] where N = number of unique IDs
        unique_ids = np.unique(volume)
        id_to_color = {rid: i for i, rid in enumerate(unique_ids)}
        remapped_volume = np.vectorize(id_to_color.get)(volume)

        total_slices = num_rows * num_cols
        axis_size = volume.shape[axis]
        slice_indices = np.linspace(0, axis_size - 1, total_slices, dtype=int)

        fig, axes = plt.subplots(num_rows, num_cols, figsize=(num_cols * 2, num_rows * 2))
        for i, ax in enumerate(axes.flat):
            idx = slice_indices[i]
            if axis == 0:
                slice_img = remapped_volume[idx, :, :]
            elif axis == 1:
                slice_img = remapped_volume[:, idx, :]
            elif axis == 2:
                slice_img = remapped_volume[:, :, idx]
            else:
                raise ValueError("Axis must be 0, 1, or 2")

            ax.imshow(slice_img, cmap=cmap)
            ax.set_title(f"Slice {idx}")
            ax.axis('off')

        plt.tight_layout()
        plt.savefig(os.path.join(self.drop_directory,save_path), dpi=300)

    def map_to_coarsened_atlas(self, data):
        # Create a lookup dictionary for original names -> ids from the original ontology
        name_to_id = {region['name']: region['id'] for region in self.ontology_dict}

        # If the input is a DataFrame
        if isinstance(data, pd.DataFrame):
            data_mapped = data.copy()
            for col in data.columns:
                # Map each region name to its corresponding coarsened region name
                data_mapped[col] = data[col].map(lambda name: self.get_coarsened_name(name, name_to_id, self.course_dict))
            return data_mapped

        # If the input is a numpy array
        elif isinstance(data, np.ndarray):
            # Map each region name to its corresponding coarsened region name
            mapped_data = np.vectorize(lambda name: self.get_coarsened_name(name, name_to_id, self.course_dict))(data)
            return mapped_data
        
        else:
            raise ValueError("Input data should be either a DataFrame or a NumPy array.")

    def get_coarsened_name(self, region_name, name_to_id, coarsened_atlas_dict):
        # Get the original region ID from the name
        original_id = name_to_id.get(region_name)
        
        # If the region ID exists in the coarsened atlas, return the coarsened name
        if original_id is not None:
            coarsened_region = coarsened_atlas_dict.get(original_id)
            if coarsened_region:
                return coarsened_region[1]  # Return the coarsened region's name
        return None  # If not found, return None
    
    @staticmethod
    def restricted_dataframe(dataframe, current_ontology_dict,colname='regionname'):
        if isinstance(current_ontology_dict, list):
            current_ontology_dict = {entry['id']: (entry['acronym'], entry['name']) for entry in current_ontology_dict}

        restricted_list = [ r'cingulate', r'nucleus accumbens', r'agranular', r'insular', r'olfactory',
                       r'auditory', r'hippocamp', r'Claustrum', r'Central linear nucleus',
                       r'Diagonal band nucleus', r'raphe', r'polor', r'limbic', r'thalamus', 
                       r'thala', r'amygdala', r'cortex', r'orbital', r'preoptic', r'Nucleus incertus', 
                       r'periaqueduct', r'parietal', r'brachial', r'Pedunculopontine tegmental nucleus', 
                       r'perirhinal', r'retrosplenial', r'nigra', r'somatosensory', r'subiculum', 
                       r'supramammillary', r'tecta', r'tegmental']
        pattern = re.compile("|".join(restricted_list), re.IGNORECASE) 
        matching_regions = [region for region, (value, name) in current_ontology_dict.items() if pattern.search(name)]
        valid_regions = {current_ontology_dict[region][1] for region in matching_regions}
        dataframe_filtered = dataframe[dataframe[colname].isin(valid_regions)].reset_index(drop=True)
        return dataframe_filtered


if __name__ == "__main__":
    # Get atlas ontology
    data_path = r'C:\Users\listo\example_registration_data\test_registration_communal_drop' 
    drop_atlas_path = os.path.join(data_path,"communal_atlas_drop/")
    atlas_json_file = os.path.join(drop_atlas_path,'structures.json')
    with open(atlas_json_file,'r') as infile:
        ontology_dict = json.load(infile)

    # Load in dataframe
    df = pd.read_csv(r'C:\Users\listo\communal_registration_logcal_drop\salience_experiment\water\df_tall.csv')
    df2 = pd.read_csv(r'C:\Users\listo\communal_registration_logcal_drop\salience_experiment\vanilla\df_tall.csv')
    df2['group'] = 'vanilla'
    df = pd.concat([df,df2])
    df['normalizedcount'] = df['normalizedcount']*100

    # Create gardener class
    atobj = AtlasGardener(ontology_dict)
    atobj()

    # Set dataframe brain regions to coarser names for simplicity
    df_regionnames = pd.DataFrame(df['regionname'])
    df_regionnames = atobj.map_to_coarsened_atlas(data=df_regionnames)
    df['regionname'] = df_regionnames

    # Restrict dataframe names to relevance list
    df_restricted = atobj.restricted_dataframe(dataframe = df, current_ontology_dict = atobj.course_dict)
