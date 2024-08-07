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
from mass_ttest import mass_ttest

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