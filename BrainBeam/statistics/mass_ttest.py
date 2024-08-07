#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" Generate statistics (# cells, cell density, t-test, p-value) and map to allen reference atlas
Written by David James Estrin """
#Import libraries
import pandas as pd
import numpy as np
from skimage.io import imread, imsave
from skimage.feature import canny as edgedetector
import matplotlib.pyplot as plt
from scipy import stats
from princeton_ara import Graph
import json
import os
import ipdb
import warnings
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw 
import io
import tqdm
import matplotlib.cm as cm
import pickle
from bootstrap import quick_boot
from injectatlas import inject_atlas

warnings.simplefilter('ignore') #Ignore warnings 

class mass_ttest(inject_atlas):
    def __init__(self,atlas_json_file,atlas_path,drop_directory,dataframe_path,abs_min_val,abs_max_val):
        super().__init__(atlas_json_file,atlas_path,drop_directory)
        self.dataframe=pd.read_csv(dataframe_path)
        self.abs_max_val=abs_max_val
        self.abs_min_val=abs_min_val

    def get_parent_level(self,level_num=0):
        """ Go through all brain regions and move one step upward on tree.
        Data is aggregated during this step. Takes the sum over brain regions
        Inputs: level_num -- an integer, when equal to 0, nothing is done to data. Else, move up one atlas level
        Outputs:DF -- returns the new dataframe where atlas level is up one. 
        """
        if level_num==0:
            return self.dataframe.groupby(['cage', 'subjectid','treatment', 'location'], as_index=False)['n'].sum()
        
        else:
            local_df = self.dataframe.groupby(['cage', 'subjectid','treatment', 'location'], as_index=False)['n'].sum()
            local_df['uid'] = local_df['cage'] + local_df['subjectid']

            # Loop over subjects in dataset
            for i,uid in enumerate(local_df['uid'].unique()):
                subset = local_df.loc[local_df['uid'] == uid]

                # Loop over brain regions
                # IMPORTANT subset is the final list .... all_regions is the list we loop over. 
                all_regions = subset['location'].unique()
                all_regions = pd.DataFrame({'location':all_regions})
                for region in all_regions['location']:
                    if region in self.tree.get_progeny_one('root')[0]:
                        continue

                    if region=='root':
                        continue

                    parent_name = self.tree.get_parent(region)
                    parent_id = self.tree.get_id(parent_name)

                    # Determine if parent structure is a child of any other regions in dataset
                    for region_check in all_regions['location']:
                        # Skip current region
                        if region_check == parent_name:
                            continue
                        else: 
                            # Get names and IDS of current region region_check
                            current_region_children_names,current_region_children_ids = self.tree.get_progeny(region_check)
                            if parent_name in current_region_children_names:
                                # the parent name is actually a child of a different structure in dataset, 
                                # so now this parent name is updated to that level
                                if region_check not in self.tree.get_progeny_one('root')[0]:
                                    parent_name = region_check
                            
                                # Update the name of the current brain region
                                subset.loc[subset['location']==region,'location']=parent_name
                            else:
                                # Update the name of the current brain region
                                if parent_name not in self.tree.get_progeny_one('root')[0]:
                                    subset.loc[subset['location']==region,'location']=parent_name

                                # Get all children of parent structure
                                parent_children_names, parent_children_ids = self.tree.get_progeny(parent_name)

                                # Determine if any other regions in dataset are children of parent
                                for parent_children in parent_children_names:
                                    if (parent_children in all_regions) and (parent_children!=region):
                                        # Change the name of the location in the dataset to the parent name
                                        subset.loc[(subset['location']==parent_children) & (parent_children!=region),'location']=parent_name

                                        # Remove the child region from all region so we do not look at it again
                                        all_regions = all_regions.drop(all_regions[all_regions['location']==parent_children].index)

                # Re-build dataframe and aggregate data again. 
                if i==0:
                    DF=subset.groupby(['cage', 'subjectid','treatment', 'location'], as_index=False)['n'].sum()
                else:
                    subset = subset.groupby(['cage', 'subjectid','treatment', 'location'], as_index=False)['n'].sum()
                    DF=pd.concat([DF,subset])
            
            return DF

    def get_normalized_n(self):
        """ Normalize each cell count by the total number of cells in each sample """
        self.dataframe['normalized_n'] = self.dataframe['n']
        self.dataframe['normalized_n'] = self.dataframe['n'].div(self.dataframe.groupby(['cage','subjectid'])['n'].transform('sum'))

    def run_injection(self,dataoh,i,level,modeoh,filenameoh):
        if modeoh=='binary':
            return
        stackoh=self.inject_data_to_stack(dataoh,level=i,mode=modeoh)
        reference_stack=self.inject_data_to_stack(dataoh,mode='reference')
        real_reference_stack=self.inject_data_to_stack(dataoh,mode='real_reference')
        self.plot_atlas(stackoh,reference_stack,real_reference_stack,filename=filenameoh)

    def __call__(self):
        """ Loop over levels and perform mass univariate t-tests,
        Note: for inherited code, this will plot anything onto brain atlas if arranged in arranged_data correctly"""
        super().__call__()
        levels=['location', 'lv1', 'lv2', 'lv3', 'lv4', 'lv5','lv6', 'lv7', 'lv8', 'lv9', 'lv10']
        for i, level in enumerate(levels):
            self.dataframe = self.get_parent_level(i)
            self.get_normalized_n() # Normalize the count data
            self.brainregions,arranged_data = self.arrange_data(level)
            self.stat_string = f'There were {len(self.brainregions[arranged_data[:,1]<0.05])} significant regions out of {len(self.brainregions)} brain regions for level {level} using raw counts'
            self.regions_to_ids(self.brainregions)
      
            # Plot data for t,p values for raw counts
            self.current_data=arranged_data
            fileoh = os.path.join(self.drop_directory,f'{level}_tvalues_raw_counts.jpg')
            self.run_injection(self.current_data[:,0],i,level,modeoh='continuous',filenameoh=fileoh) #Raw, t-value
            fileoh = os.path.join(self.drop_directory,f'{level}_pvalues_raw_counts.jpg')
            self.run_injection(self.current_data[:,1],i,level,modeoh='binary',filenameoh=fileoh) #Raw, p-value

            # Normalized counts
            self.brainregions,arranged_data = self.arrange_data(level,counttype='normalized_n')
            self.stat_string = f'There were {len(self.brainregions[arranged_data[:,1]<0.05])} significant regions out of {len(self.brainregions)} brain regions for level {level} using normalized counts'
            self.regions_to_ids(self.brainregions)

            # Plot data for t,p values for normalized counts
            self.current_data=arranged_data
            fileoh = os.path.join(self.drop_directory,f'{level}_tvalues_normalized_counts.jpg')
            self.run_injection(self.current_data[:,0],i,level,modeoh='continuous',filenameoh=fileoh) #Raw, t-value
            fileoh = os.path.join(self.drop_directory,f'{level}_pvalues_normalized_counts.jpg')
            self.run_injection(self.current_data[:,1],i,level,modeoh='binary',filenameoh=fileoh) #Raw, p-value
        return

    def arrange_data(self,level_name,counttype='n'):
        # Calculate number subjects by group
        self.dataframe["uid"] = self.dataframe["cage"] + self.dataframe["subjectid"]
        gn=self.dataframe.groupby('treatment')['uid'].nunique()
        
        # Parse data into data only necessary for running t test
        level_name = 'location'
        local_df = self.dataframe #.groupby(['cage', 'subjectid','treatment', level_name], as_index=False)[counttype].sum()
        local_np = local_df.to_numpy()
        colnum=local_df.columns.get_loc(level_name)
        self.brainregions=np.unique(local_np[:,colnum])

        arranged_data=[]
        self.regions_to_ids(self.brainregions)
        for region in self.brainregions:
            regiondf=local_df.loc[local_df [level_name] == region]
            dfg = regiondf.groupby('treatment')
            if dfg.ngroups>1:
                get_values=[]
                for group_name, df_group in dfg:
                    get_values.append(df_group[counttype].to_numpy())

                control = np.pad(get_values[0],(0,1+gn[0]-len(get_values)),'constant',constant_values=0)
                control=quick_boot(control)
                experimental = np.pad(get_values[1],(0,1+gn[1]-len(get_values)),'constant',constant_values=0)
                experimental=quick_boot(experimental)
                t_stat,p_value=self.ttest(control,experimental)

                # Prevent infinity error
                if t_stat==float("inf"):
                    t_stat=1
                elif t_stat==float("-inf"):
                    t_stat=-1

                t_stat=t_stat*-1 # Doing this so that red means (Experimental>control) and blue means (control>experimental)
                arranged_data.append([t_stat,p_value])
            else:
                arranged_data.append([np.nan,np.nan])

        # Convert back to numpy array
        arranged_data=np.asarray(arranged_data)
 
        # Apply FDR
        arranged_data = self.false_discovery_rate_adjusted(arranged_data)
        return self.brainregions,arranged_data

    def ttest(self,group1,group2):
        """ Run univariate t-test """
        return stats.ttest_ind(group1, group2) # returns t_stat and p_value
    
    def false_discovery_rate_adjusted(self,data,alpha=0.1):
        """Calculated false discovery rate via Benjamini-Hochberg procedure """
        pvalues = data[:,1] # get pvalues
        pvalues = pvalues[~np.isnan(pvalues)] #remove nan pvalues
        pvalues.sort() #sort pvalues

        # Do Benjamini-Hochberg procedure:
        m = len(pvalues)
        
        # Calculate k/m*alpha
        index = -1 # Set threshold for significance
        for k,p in enumerate(pvalues):
            kma = ((k+1)/m)*alpha
            if p<kma:
                index=k
                final_p,finalkma=p,kma

        # Adjust p values 
        adjusted_ps = []
        for k,p in enumerate(pvalues):
            adjusted_p = (m*p)/(k+1)
            if adjusted_p<1:
                adjusted_ps.append(adjusted_p)
            else:
                adjusted_ps.append(1)

        # put adjusted p value back into data
        for L,p_original in enumerate(data[:,1]):
            for p,padjust in zip(pvalues,adjusted_ps):
                if p_original == p:
                    data[L,1]=padjust
        return data
    
    @classmethod
    def load(cls,filename):
        """Load an instance from a pickle file."""
        with open(filename, "rb") as file:
            return pickle.load(file)
    
    def save(self,filename):
        """Save the instance to a file using pickle."""
        with open(filename, "wb") as file:
            pickle.dump(self, file)
    
class total_counts(mass_ttest):
    def __call__(self):
        """ Loop over levels and perform mass univariate t-tests,
        Note: for inherited code, this will plot anything onto brain atlas if arranged in arranged_data correctly"""
        inject_atlas.__call__(self) #call grand parent method for __call__, we do not want parent method
        levels=['location', 'lv1', 'lv2', 'lv3', 'lv4', 'lv5','lv6', 'lv7', 'lv8', 'lv9', 'lv10']
        for i, level in enumerate(levels):
            self.dataframe = self.get_parent_level(i)
            self.get_normalized_n() # Normalize the count data
            self.brainregions,arranged_data = self.arrange_data(level)
            self.stat_string = f'There were {len(self.brainregions[arranged_data[:,1]<0.05])} significant regions out of {len(self.brainregions)} brain regions for level {level} using raw counts'
            self.regions_to_ids(self.brainregions)
      
            # Plot data for t,p values for raw counts
            self.current_data=arranged_data
            fileoh = os.path.join(self.drop_directory,f'{level}total_raw_counts.jpg')
            self.run_injection(self.current_data[:,0],i,level,modeoh='continuous',filenameoh=fileoh) #Raw counts, total

            fileoh = os.path.join(self.drop_directory,f'{level}celldensity_raw_counts.jpg')
            self.run_injection(self.current_data[:,1],i,level,modeoh='continuous',filenameoh=fileoh) #Raw counts, cell density

            # Normalized counts
            self.brainregions,arranged_data = self.arrange_data(level,counttype='normalized_n')
            self.stat_string = f'There were {len(self.brainregions[arranged_data[:,1]<0.05])} significant regions out of {len(self.brainregions)} brain regions for level {level} using normalized counts'
            self.regions_to_ids(self.brainregions)

            # Plot data for t,p values for normalized counts
            self.current_data=arranged_data
            fileoh = os.path.join(self.drop_directory,f'{level}total_normalized_counts.jpg')
            self.run_injection(self.current_data[:,0],i,level,modeoh='continuous',filenameoh=fileoh) #Normalized counts, total

            fileoh = os.path.join(self.drop_directory,f'{level}celldensity_normalized_counts.jpg')
            self.run_injection(self.current_data[:,1],i,level,modeoh='continuous',filenameoh=fileoh) #Normalized counts, cell density
        return
    
    def arrange_data(self,level_name,counttype='n'):
        # Calculate number subjects by group
        self.dataframe["uid"] = self.dataframe["cage"] + self.dataframe["subjectid"]
        gn=self.dataframe.groupby('treatment')['uid'].nunique()
        
        # Parse data into data only necessary for running t test
        level_name = 'location'
        local_df = self.dataframe #.groupby(['cage', 'subjectid','treatment', level_name], as_index=False)[counttype].sum()
        local_np = local_df.to_numpy()
        colnum=local_df.columns.get_loc(level_name)
        self.brainregions=np.unique(local_np[:,colnum])

        arranged_data=[]
        self.regions_to_ids(self.brainregions)
        for region in self.brainregions:
            regiondf=local_df.loc[local_df [level_name] == region]
            dfg = regiondf.groupby('treatment')
            if dfg.ngroups>1:
                get_values=[]
                for group_name, df_group in dfg:
                    get_values.append(df_group[counttype].to_numpy())

                control = np.pad(get_values[0],(0,1+gn[0]-len(get_values)),'constant',constant_values=0)
                experimental = np.pad(get_values[1],(0,1+gn[1]-len(get_values)),'constant',constant_values=0)
    
                # Quickly count the total number of cells per region
                try:
                    total_value = np.concatenate((experimental,control),axis=0)
                except:
                    ipdb.set_trace()
                voloh = (self.volumes[np.where(self.volumes[:,0]==self.ids[np.where(self.brainregions==region)[0][0]])[0][0],1])/(1e+9) # get volume in cubic mm
                celldensity=total_value/voloh
                density_value = np.nanmean(celldensity)
                total_value = np.nanmean(total_value)
                arranged_data.append([total_value,density_value])
            elif dfg.ngroups==1:
                if np.asarray(regiondf['treatment'])[0]=='CORTEXPERIMENTAL':
                    control = np.pad([0],(0,1+gn[0]-1),'constant',constant_values=0)
                    experimental = np.pad(regiondf['n'],(0,1+gn[1]-1),'constant',constant_values=0)
                else:
                    control = np.pad(regiondf['n'],(0,1+gn[0]-1),'constant',constant_values=0)
                    experimental = np.pad([0],(0,1+gn[1]-1),'constant',constant_values=0)

                # Quickly count the total number of cells per region
                total_value = np.concatenate((experimental,control),axis=0)
                voloh = (self.volumes[np.where(self.volumes[:,0]==self.ids[np.where(self.brainregions==region)[0][0]])[0][0],1])/(1e+9) # get volume in cubic mm
                celldensity=total_value/voloh
                density_value = np.nanmean(celldensity)
                total_value = np.nanmean(total_value)
                arranged_data.append([total_value,density_value])

            else:
                ipdb.set_trace()
                arranged_data.append([np.nan,np.nan])

        # Convert back to numpy array
        arranged_data=np.asarray(arranged_data)
        return self.brainregions,arranged_data
    
    @classmethod
    def load(cls,filename):
        """Load an instance from a pickle file."""
        with open(filename, "rb") as file:
            return pickle.load(file)
    
    def save(self,filename):
        """Save the instance to a file using pickle."""
        with open(filename, "wb") as file:
            pickle.dump(self, file)

if __name__=='__main__':
    # Run mass univariate t-tests
    filename_massttest = r'C:\Users\listo\BRAINBEAM\BRAINBEAM\statistics\datasets\mass_ttests_obj.pkl'
    if os.path.isfile(filename_massttest):
        massttest_obj=mass_ttest.load(filename_massttest)
    else:
        massttest_obj=mass_ttest(atlas_json_file = r'C:\Users\listo\BRAINBEAM\BRAINBEAM\statistics\datasets\ara_ontology.json',
                        atlas_path=r'C:\Users\listo\BRAINBEAM\BRAINBEAM\statistics\datasets\ara_annotation_10um.tif',
                        drop_directory=r'C:\Users\listo\BRAINBEAM\BRAINBEAM\statistics\figures',
                        dataframe_path=r'C:\Users\listo\BRAINBEAM\BRAINBEAM\statistics\datasets\rabies_cort_cohort2_dataset.csv',
                        abs_min_val=-4,
                        abs_max_val=4)
        massttest_obj()
        massttest_obj.save(filename_massttest)

    # Run analysis on counts
    filename_counts = r'C:\Users\listo\BRAINBEAM\BRAINBEAM\statistics\datasets\total_counts_obj.pkl'
    if os.path.isfile(filename_counts):
        total_counts_obj=total_counts.load(filename_counts)
    else:
        total_counts_obj=total_counts(atlas_json_file = r'C:\Users\listo\BRAINBEAM\BRAINBEAM\statistics\datasets\ara_ontology.json',
                        atlas_path=r'C:\Users\listo\BRAINBEAM\BRAINBEAM\statistics\datasets\ara_annotation_10um.tif',
                        drop_directory=r'C:\Users\listo\BRAINBEAM\BRAINBEAM\statistics\figures',
                        dataframe_path=r'C:\Users\listo\BRAINBEAM\BRAINBEAM\statistics\datasets\rabies_cort_cohort2_dataset.csv',
                        abs_min_val=0,
                        abs_max_val=10)
        total_counts_obj()
        total_counts_obj.save(filename_counts)
