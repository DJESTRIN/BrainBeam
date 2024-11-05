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
import seaborn as sns
from datetime import datetime

warnings.simplefilter('ignore') #Ignore warnings 

class mass_ttest(inject_atlas):
    def __init__(self,atlas_json_file,atlas_path,drop_directory,dataframe_path):
        super().__init__(atlas_json_file,atlas_path,drop_directory)
        self.dataframe=pd.read_csv(dataframe_path)

    def calculate_max_min_color_range(self,data):
        """ Get max and min values via percentiles of dataframe """
        self.abs_min_val = -2 #np.nanpercentile(data,20)
        self.abs_max_val = 2 #np.nanpercentile(data,80)
        return

    def get_parent_level(self,level_num=0):
        """ Go through all brain regions and move one step upward on tree.
        Data is aggregated during this step. Takes the sum over brain regions
        Inputs: level_num -- an integer, when equal to 0, nothing is done to data. Else, move up one atlas level
        Outputs:DF -- returns the new dataframe where atlas level is up one. 
        """
        def save_full_long_format(df,level_num):
            # Generate a full long format of data frame where missing regions are assumed to have n=0
            
            unique_subjects_cages = df[['subjectid', 'cage','treatment']].drop_duplicates()
            unique_brain_regions = df['location'].unique()
            complete_index = pd.MultiIndex.from_product(
                [unique_subjects_cages['subjectid'], unique_subjects_cages['cage'], unique_brain_regions], 
                names=['subjectid', 'cage', 'location'])
            complete_df = pd.DataFrame(index=complete_index).reset_index()
            df = pd.merge(complete_df, df, on=['subjectid', 'cage', 'location'], how='left')
            df['n'] = df['n'].fillna(0)
            df = pd.merge(df, df[['subjectid', 'cage', 'treatment']].drop_duplicates(), on=['subjectid', 'cage','treatment'], how='left')
            output_file=os.path.join(self.drop_directory,f'conors_dataframe_format_level{level_num}.csv')
            df.to_csv(output_file)

        if level_num==0:
            save_full_long_format(self.dataframe.groupby(['cage', 'subjectid','treatment', 'location'], as_index=False)['n'].sum(),level_num)
            return self.dataframe.groupby(['cage', 'subjectid','treatment', 'location'], as_index=False)['n'].sum()
        
        else:
            # Generate my version of dataframe
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
                    if parent_name=='root':
                        parent_name=region
                    
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

                save_full_long_format(DF,level_num)
            
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
        levels=['location', 'lv1', 'lv2', 'lv3'] #, 'lv4', 'lv5','lv6', 'lv7', 'lv8', 'lv9', 'lv10']
        for i, level in enumerate(levels):
            print(f'Currently on level: {level}')
            self.dataframe = self.get_parent_level(i)
            output_datafile = os.path.join(self.drop_directory,f'{level}_counts_per_level.csv')
            self.dataframe.to_csv(output_datafile)
            self.get_normalized_n() # Normalize the count data
            self.brainregions,arranged_data = self.arrange_data(level)
            self.stat_string = f'There were {len(self.brainregions[arranged_data[:,1]<0.05])} significant regions out of {len(self.brainregions)} brain regions for level {level} using raw counts'
            self.regions_to_ids(self.brainregions)
        
            # Plot data for t,p values for raw counts
            self.current_data=self.drop_tvalues(arranged_data)
            fileoh = os.path.join(self.drop_directory,f'{level}_tvalues_raw_counts.jpg')
            self.calculate_max_min_color_range(self.current_data[:,0])
            self.run_injection(self.current_data[:,0],i,level,modeoh='continuous',filenameoh=fileoh) #Raw, t-value

            # Normalized counts
            self.brainregions,arranged_data = self.arrange_data(level,counttype='normalized_n')
            self.stat_string = f'There were {len(self.brainregions[arranged_data[:,1]<0.05])} significant regions out of {len(self.brainregions)} brain regions for level {level} using normalized counts'
            self.regions_to_ids(self.brainregions)

            # Plot data for t,p values for normalized counts
            self.current_data=self.drop_tvalues(arranged_data)
            fileoh = os.path.join(self.drop_directory,f'{level}_tvalues_normalized_counts.jpg')
            self.calculate_max_min_color_range(self.current_data[:,0])
            self.run_injection(self.current_data[:,0],i,level,modeoh='continuous',filenameoh=fileoh) #Raw, t-value
        return
    
    def drop_tvalues(self,data):
        if hasattr(self, 'drop_tvals') and self.drop_tvals:
            data[(data[:,0]<self.drop_threshold) & (data[:,0]>-self.drop_threshold),0]=np.nan
            return data
        else:
            return data

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

                # Bootstrap data is true
                if hasattr(self, 'bootstrap') and self.bootstrap:
                    control=quick_boot(control)
                    experimental=quick_boot(experimental)
                
                t_stat,p_value=self.ttest(control,experimental)

                # Prevent infinity error
                if t_stat==float("inf"):
                    t_stat=10
                elif t_stat==float("-inf"):
                    t_stat=-10

                t_stat=t_stat*-1 # Doing this so that red means (Experimental>control) and blue means (control>experimental)
                arranged_data.append([t_stat,p_value])
            else:
                arranged_data.append([np.nan,np.nan])

        # Convert back to numpy array
        arranged_data=np.asarray(arranged_data)

        # Plot kernel density of t-values
        outputfile=os.path.join(self.drop_directory,f'{level_name}_kerneldensity_tvalues.jpg')
        self.kernel_density(pd.DataFrame({'t-values':arranged_data[:,0]}),outputfile)
 
        # Apply FDR
        arranged_data = self.false_discovery_rate_adjusted(arranged_data)
        return self.brainregions,arranged_data
    
    def kernel_density(self,data,filename):
        plt.figure()
        sns.set_style('whitegrid')
        sns.histplot(data=data, x="t-values", kde=True)
        plt.savefig(filename)
        plt.close()

    def ttest(self,group1,group2):
        """ Run univariate t-test """
        return stats.ttest_ind(group1, group2) # returns t_stat and p_value
    
    def false_discovery_rate_adjusted(self,data,alpha=0.05):
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
    
def create_timestamped_directory(root_dir):
    current_time = datetime.now()
    timestamp = current_time.strftime("%Y%m%d_%H%M%S")
    dir_name = f"{root_dir}_{timestamp}"
    os.makedirs(dir_name, exist_ok=True)
    return dir_name

if __name__=='__main__':
    # Run mass univariate t-tests
    filename_massttest = r'C:\Users\listo\level_analysis\datasets\mass_ttests_obj3.pkl'
    if os.path.isfile(filename_massttest):
        massttest_obj=mass_ttest.load(filename_massttest)
    else:
        output = create_timestamped_directory(r'C:\Users\listo\level_analysis\results')
        massttest_obj=mass_ttest(atlas_json_file = r'C:\Users\listo\BRAINBEAM\BRAINBEAM\statistics\datasets\ara_ontology.json',
                        atlas_path=r'C:\Users\listo\BRAINBEAM\BRAINBEAM\statistics\datasets\ara_annotation_10um.tif',
                        drop_directory=output,
                        dataframe_path=r'C:\Users\listo\level_analysis\datasets\rabies_cort_cohort2_dataset.csv')
        
        # Threshold T-values for dataframe
        massttest_obj.drop_tvals=True
        massttest_obj.drop_threshold=1.3

        #Run object pipeline
        massttest_obj()
        massttest_obj.save(filename_massttest)