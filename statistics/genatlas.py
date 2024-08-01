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

warnings.simplefilter('ignore') #Ignore warnings 

class inject_atlas():
    """ This class is used to generate atlas graphics as well as calculate common underlying stats """
    def __init__(self,atlas_json_file=[],atlas_path=[],drop_directory=[]):
        self.atlas_path=atlas_path
        self.drop_directory=drop_directory
        try:
            os.mkdir(self.drop_directory)
        except:
            print('output dir is already made')

        #Set up ARA tree
        with open(atlas_json_file,'r') as infile:
            ontology_dict = json.load(infile)
        self.tree=Graph(ontology_dict)
    
    def __call__(self,):
        """ collect common info: 
        Get atlas, calculate atlas volumes and count regions """
        self.get_atlas_stack()
        self.get_atlas_stack_volumes()
        self.count_regions_atlas()

    def get_atlas_stack(self):
        """ Open image as a numpy array """
        self.atlas_stack=imread(self.atlas_path)
        self.atlas_stack=np.squeeze(np.array(self.atlas_stack))
        self.atlas_stack=self.atlas_stack.astype('float')
        return
    
    def get_atlas_stack_volumes(self):
        """ Get the volume of each brain region... to calculate cell density """
        volume_file = self.drop_directory+r'\atlas_volumes.npy' #the output file for the volume data
        if os.path.isfile(volume_file):
            self.volumes = np.load(volume_file)
        else:
            volumes=[]
            for unid in tqdm.tqdm(np.unique(self.atlas_stack)):
                if unid==0:
                    continue
                else:
                    pixels = np.where(self.atlas_stack==unid)
                    if len(pixels[0])>0:
                        volumeoh=len(pixels[0])*1000 # 10um * 10um * 10 um ---> gives cubic um
                    else:
                        volumeoh=0
                    volumes.append([unid,volumeoh])
            volumes = np.asarray(volumes)
            np.save(volume_file,volumes)
            self.volumes=volumes
    
    def count_regions_atlas(self):
        """ Get all brain regions in numpy stack """
        self.all_atlas_regions = np.unique(self.atlas_stack)
        self.total_regions = len(self.all_atlas_regions)

        # Calculate what percent of regions in atlas are inside our tree.
        conserved=0
        allnames,allids=self.tree.get_progeny(nodename='root')
        for idoh in self.all_atlas_regions:
            for idtreeoh in allids:
                if idoh==idtreeoh:
                    conserved+=1
        print(f'{conserved/self.total_regions} % of the atlas is conserved in corresponding tree. ')


    def regions_to_ids(self,brainregions):
        """ Searches for brainregions in ARA tree and finds corresponding ID """
        ids=[]
        for region in brainregions:
            ids.append(self.tree.graph[str(region)].ID)
        self.ids=np.array(ids)

    def inject_data_to_stack(self,data,skip_frames=90,mode='continuous',threshold=0.1,level=0):
        """ Take data of interest and inject it into the ARA stack """
        injected_slices=[] # Final list of colored slices
        pbar2 = tqdm.tqdm(total=15, desc='Slice Number:',position=1,leave=True)
        for sn in range(1,self.atlas_stack.shape[2]):
            if (sn%skip_frames)==0:
                # Get current slice from stack
                slicea=self.atlas_stack[:,:,sn]

                # Set background of image to nan
                background=stats.mode(slicea) 
                background=background[0][0]
                slicea[np.where(slicea==background)]=np.nan  

                #Copy current slice as the final output slice      
                slicec=np.full([slicea.shape[0], slicea.shape[1]], np.nan)

                """Switch Case --- mode must match one of three categories:
                 1. continous is for data such as t-values where you want to see range
                 2. binary is for data with a cut off. Ex. pvalue<0.05
                 3. Reference is a special case where reference atlas is plotted. """
                if mode=='continuous':
                    # Loop through brain regions
                    collected=[]
                    for name,id in zip(self.brainregions,self.ids):
                        collected.append(name)
                        value = data[np.where(self.ids==id)] # Get the value if not nan
                        slicec[np.where(slicea==id)]=value

                        progeny_names,progeny_ids = self.tree.get_progeny(nodename=str(name)) # Get progeny for each brain region
                        if progeny_ids:
                            for progeny_name, progeny_id in zip(progeny_names,progeny_ids):
                                if progeny_name in collected:
                                    continue
                                else:
                                    collected.append(progeny_name)

                                slicec[np.where(slicea==progeny_id)]=value

                elif mode=='binary':
                    for i in np.unique(slicea):
                        value=data[np.where(self.ids==i)]
                        if value<threshold:
                            new_value=5
                        else:
                            new_value=-5
                        slicec[np.where(slicea==i)]=new_value

                elif mode=='reference':
                    counter=1
                    for i in np.unique(slicea):
                        slicec[np.where(slicea==i)]=counter
                        counter+=1.100000000000000123

                elif mode=='real_reference':
                    for i in np.unique(slicea):
                        slicec[np.where(slicea==i)]=i

                else:
                    raise Exception("Mode does not match continous, binary or reference formats. Please check mode setting")
                
                #Append the colored in slice to list of slices
                injected_slices.append(slicec)
                pbar2.update(1)
            pbar2.close()
        return injected_slices

    def plot_atlas(self,stack,reference_stack,real_reference_stack,add_scalebar=True, filename = r'C:\Users\listo\example.pdf'):
        """ Method for plotting coronal slices onto a grid with scale bar and acronym references
        stack -- main data stack
        reference_stack -- the reference image for the ARA
        real_reference_stack -- ARA image stack without my manipulations
        """
        # Get number of rows and columns
        rows=np.floor(np.sqrt(len(stack))) 
        columns=np.floor(len(stack)/rows)

        #Convert data to numpy array
        stacknp=np.asarray(stack)
        all_slices=np.full((int(stacknp.shape[2]*rows), int(stacknp.shape[1]*columns), 3), 255) # Get white image

        #Create figure
        fig, axes = plt.subplots(nrows=int(rows), ncols=int(columns))
        current_row,current_column=0,0
        starting_row_value,starting_column_value=0,0
        all_acronym_data=[]

        #Loop over rows and columns
        for i,ax in enumerate(axes.flat):
            if i>(rows*columns):
                continue
            coronal_slice, region_data = self.plot_coronal_slice(stack[i],reference_stack[i],real_reference_stack[i]) #Plot coronal slice on hand
            all_acronym_data.append(region_data) #Add acronyms to common list
            coronal_slice = np.asarray(coronal_slice) #convert coronal slice to numpy

            all_slices[starting_row_value:int(starting_row_value+stacknp.shape[2]),starting_column_value:int(starting_column_value+stacknp.shape[1])]=coronal_slice

            # Adjust the rows and columns so coronal slice fits into final image
            current_column+=1
            if current_column>=columns:
                current_column=0
                current_row+=1
                if current_row>=rows:
                    current_row=0
                starting_row_value=int(current_row*stacknp.shape[2])
            starting_column_value=int(current_column*stacknp.shape[1])
        
        # Generate scale bar
        if add_scalebar:
            scale_bar_oh = self.generate_scale_bar()
            blank = np.full((all_slices.shape[0],200,3),255)
            blank[800:1600,:,:]=scale_bar_oh
            all_slices=np.concatenate((all_slices,blank),axis=1)

        # Add legend to bottom
        # if add_legend:
        #     all_slices = self.add_labels(all_slices, all_acronym_data)

        #Convert back to PIL
        holder = all_slices.shape[1]
        all_slices=Image.fromarray(all_slices.astype('uint8'), 'RGB')
        draw = ImageDraw.Draw(all_slices)
        font = ImageFont.truetype( r'C:\Windows\Fonts\Arial.ttf', 60)
        draw.text((10,10),self.stat_string,(0,0,0),align='left',font=font)
        draw.text((holder-220,700),f'max: {self.abs_max_val}',(0,0,0),align='left',font=font)
        draw.text((holder-220,1600),f'min: {self.abs_min_val}',(0,0,0),align='left',font=font)
        all_slices.save(filename)
        return
    
    def quick_show(self,data):
        plt.figure()
        plt.imshow(data)
        plt.show()

    def generate_scale_bar(self,height=800, width=200, padding=10):
        # Choose the colormap
        colormap = cm.jet
        scale_bar_height = height - 2 * padding
        scale_bar = np.linspace(self.abs_min_val, self.abs_max_val, scale_bar_height)
        scale_bar = np.tile(scale_bar, (width - 2 * padding, 1))  # make it a horizontal bar
        normalized_scale_bar = (scale_bar - self.abs_min_val) / (self.abs_max_val - self.abs_min_val) # Normalize the scale bar to [0, 1]
        color_scale_bar = colormap(normalized_scale_bar)[:, :, :3]  # Apply the colormap to the scale bar and discard the alpha channel
        color_scale_bar = (color_scale_bar * 255).astype(np.uint8) # Convert to 0-255 range and uint8
        imoh=Image.fromarray(color_scale_bar)
        imoh=imoh.rotate(90,expand=1)
        wity=width-(2*padding)
        hity=height-(2*padding)
        imoh=imoh.resize((wity,hity))
        imoh=np.asarray(imoh)
        image = np.ones((height, width, 3), dtype=np.uint8) * 255  # white background
        image[padding:height-padding, padding:width-padding,:] = imoh  # embed scale bar in the center
        return image
    
    def add_labels(self,image,label_data):
        """ NOT CURRENTLY USED:
         Will add labels to the final image at the bottom of image"""
        # Convert label data into numpy array
        all_regions=[]
        for slice in label_data:
            for region in slice:
                all_regions.append(region)
        all_regions=np.asarray(all_regions)

        un_regions=[]
        for uin in np.unique(all_regions[:,0]):
            acoh = all_regions[np.where(all_regions[:,0]==uin)[0][0],1]
            un_regions.append([uin,acoh])
        un_regions=np.asarray(un_regions)

        # Add labels to blank image
        counter=0
        spacer=0.02
        x_start,y_start=0,0
        fig = plt.figure(figsize=(15,5))
        for region in un_regions:
            # Get name and acro
            name,acro=region
            string=f'{acro}:{name}'

            # plot based on coordinates
            plt.figtext(y_start, x_start, string, size=6)

            # alter coordinates
            x_start+=spacer
            if x_start>0.95:
                x_start=0
                y_start+=0.15

        plt.axis('off')
        buf = io.BytesIO() 
        fig.savefig(buf) 
        img = Image.open(buf)
        img = img.resize((image.shape[1],int(round(image.shape[0]/2))))
        img = np.asarray(img)

        # Vertical concat to big image
        img=img[:,:,:-1]
        image = np.concatenate((image,img),axis=0)
        return image

    def plot_coronal_slice(self,image,reference_image,real_reference_image):
        # Cut data image so only right side
        image=image.T
        real_reference_image=real_reference_image.T
        height,width=image.shape
        image=image[:,-1*int(round(width/2)):]

        # Get edges of reference image
        reference_image = reference_image.T
        reference_image_copy = np.copy(reference_image) # Make a copy for later when getting labels
        reference_image = np.nan_to_num(reference_image) # convert nan back to 0
        edges = edgedetector(image=reference_image,sigma=1)
        edges = edges*-1 #Flip coloring of image

        # Make copy of reference image and cut it to left side
        height,width=edges.shape
        edges_cpy=edges[:,:int(round(width/2))]
        edges_right=edges[:,-int(round(width/2)):]
        reference_image_copy=reference_image_copy[:,:int(round(width/2))]
        real_reference_image=real_reference_image[:,:int(round(width/2))]

        # Add acronyms to left side of image
        region_data=self.get_brain_region_labels(real_reference_image.T)

        # Convert data image to RGB
        colormap = cm.jet # get jet colormap
        normalized_pixel_values = (image - self.abs_min_val) / (self.abs_max_val - self.abs_min_val) # Normalize pixel values to range [0, 1]
        converted_image = colormap(normalized_pixel_values)[:,:,:3] # Apply the colormap

        #Convert black pixels to white
        for i,row in enumerate(converted_image):
            for j,pixel in enumerate(row):
                if pixel[0]==0 and pixel[1]==0 and pixel[2]==0:
                    converted_image[i,j,:]=[1,1,1]
        converted_image=np.round(converted_image*255).astype(np.uint8)

        # Add edge data to image 
        pixelsx,pixelsy=np.where(edges_right!=0)
        for x,y in zip(pixelsx,pixelsy):
            converted_image[x,y,:] = [0,0,0]

        # Add Left side of image, which is the atlas
        left_image = np.full((edges_cpy.shape[0], edges_cpy.shape[1], 3), 255)
        pixelsx,pixelsy=np.where(edges_cpy!=0)
        for x,y in zip(pixelsx,pixelsy):
            left_image[x,y,:] = [0,0,0]
        final_coronal_slice=np.concatenate((left_image,converted_image),axis=1)
        PIL_image = Image.fromarray(final_coronal_slice.astype('uint8'), 'RGB')

        # Add acronyms to image
        draw = ImageDraw.Draw(PIL_image)
        font = ImageFont.truetype( r'C:\Windows\Fonts\Arial.ttf', 15)
        for corresponding_name,acronym,xav,yav in region_data:
            string=f'{acronym}: {np.round((self.current_data[np.where(self.brainregions==corresponding_name)[0],0][0]*100))/100}'
            draw.text((xav, yav),string,(0,0,0),font=font,align='center')
            self.current_data[np.where(self.brainregions==corresponding_name)[0],0][0]
        return PIL_image, region_data

    def get_brain_region_labels(self,reference_image):
        """ Gets list containing acronym, name , X and Y coordinates for current image brain regions """
        final_list=[]
        for region in np.unique(reference_image)[:-1]:
            try:
                outputs=np.where(self.ids==region)
                corresponding_name = self.brainregions[outputs[0]][0]
            except:
                continue

            #get acronym
            words = corresponding_name.split(' ')
            words = [word for word in words if (word != 'of' or word != 'the' or word != 'in' or word != 'layer' or word != 'part' or word != 'area')]
            acronym = [word[0] for word in words]
            acronym = ''.join(acronym)
            acronym = acronym.upper()

            #get coordinates
            xall,yall=np.where(reference_image==region)
            pull=np.random.randint(len(xall))
            xav,yav=xall[pull],yall[pull]
            
            #Append to final list
            final_list.append([corresponding_name,acronym,xav,yav])
        return final_list


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
        stackoh=self.inject_data_to_stack(dataoh,level=i,mode=modeoh)
        reference_stack=self.inject_data_to_stack(dataoh,mode='reference')
        real_reference_stack=self.inject_data_to_stack(dataoh,mode='real_reference')
        self.plot_atlas(stackoh,reference_stack,real_reference_stack,filename=filenameoh)

    def __call__(self):
        """ Loop over levels and perform mass univariate t-tests,
        Note: for inherited code, this will plot anything onto brain atlas if arranged in arranged_data correctly"""
        super().__call__()
        levels=['location', 'lv1', 'lv2', 'lv3', 'lv4', 'lv5','lv6', 'lv7', 'lv8', 'lv9', 'lv10']
        pbar1 = tqdm.tqdm(total=len(levels), desc='Level Number:',leave=True,position=0)
        for i, level in enumerate(levels):
            self.dataframe = self.get_parent_level(i)
            self.get_normalized_n() # Normalize the count data
            self.brainregions,arranged_data = self.arrange_data(level)
            self.stat_string = f'There were {len(self.brainregions[arranged_data[:,1]<0.05])} significant regions out of {len(self.brainregions)} brain regions for level {level} using raw counts'
            self.regions_to_ids(self.brainregions)
      
            # Plot data for t,p values for raw counts
            self.current_data=arranged_data
            fileoh = os.path.join(r'C:\Users\listo',f'{level}_tvalues_raw_counts.pdf')
            self.run_injection(self.current_data[:,0],i,level,modeoh='continuous',filenameoh=fileoh) #Raw, t-value
            fileoh = os.path.join(r'C:\Users\listo',f'{level}_pvalues_raw_counts.pdf')
            self.run_injection(self.current_data[:,1],i,level,modeoh='binary',filenameoh=fileoh) #Raw, p-value

            # Normalized counts
            self.brainregions,arranged_data = self.arrange_data(level,counttype='normalized_n')
            self.stat_string = f'There were {len(self.brainregions[arranged_data[:,1]<0.05])} significant regions out of {len(self.brainregions)} brain regions for level {level} using normalized counts'
            self.regions_to_ids(self.brainregions)

            # Plot data for t,p values for normalized counts
            self.current_data=arranged_data
            fileoh = os.path.join(r'C:\Users\listo',f'{level}_tvalues_normalized_counts.pdf')
            self.run_injection(self.current_data[:,0],i,level,modeoh='continuous',filenameoh=fileoh) #Raw, t-value
            fileoh = os.path.join(r'C:\Users\listo',f'{level}_pvalues_normalized_counts.pdf')
            self.run_injection(self.current_data[:,1],i,level,modeoh='binary',filenameoh=fileoh) #Raw, p-value
            pbar1.update(1)
        pbar1.close()
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
    
class total_counts(mass_ttest):
    def __call__(self):
        """ Loop over levels and perform mass univariate t-tests,
        Note: for inherited code, this will plot anything onto brain atlas if arranged in arranged_data correctly"""
        inject_atlas.__call__(self) #call grand parent method for __call__, we do not want parent method
        levels=['location', 'lv1', 'lv2', 'lv3', 'lv4', 'lv5','lv6', 'lv7', 'lv8', 'lv9', 'lv10']
        pbar1 = tqdm.tqdm(total=len(levels), desc='Level Number:',leave=True,position=0)
        for i, level in enumerate(levels):
            self.dataframe = self.get_parent_level(i)
            self.get_normalized_n() # Normalize the count data
            self.brainregions,arranged_data = self.arrange_data(level)
            self.stat_string = f'There were {len(self.brainregions[arranged_data[:,1]<0.05])} significant regions out of {len(self.brainregions)} brain regions for level {level} using raw counts'
            self.regions_to_ids(self.brainregions)
      
            # Plot data for t,p values for raw counts
            self.current_data=arranged_data
            fileoh = os.path.join(r'C:\Users\listo',f'{level}total_raw_counts.pdf')
            self.run_injection(self.current_data[:,0],i,level,modeoh='continuous',filenameoh=fileoh) #Raw counts, total

            fileoh = os.path.join(r'C:\Users\listo',f'{level}celldensity_raw_counts.pdf')
            self.run_injection(self.current_data[:,1],i,level,modeoh='continuous',filenameoh=fileoh) #Raw counts, cell density

            # Normalized counts
            self.brainregions,arranged_data = self.arrange_data(level,counttype='normalized_n')
            self.stat_string = f'There were {len(self.brainregions[arranged_data[:,1]<0.05])} significant regions out of {len(self.brainregions)} brain regions for level {level} using normalized counts'
            self.regions_to_ids(self.brainregions)

            # Plot data for t,p values for normalized counts
            self.current_data=arranged_data
            fileoh = os.path.join(r'C:\Users\listo',f'{level}total_normalized_counts.pdf')
            self.run_injection(self.current_data[:,0],i,level,modeoh='continuous',filenameoh=fileoh) #Normalized counts, total

            fileoh = os.path.join(r'C:\Users\listo',f'{level}celldensity_normalized_counts.pdf')
            self.run_injection(self.current_data[:,1],i,level,modeoh='continuous',filenameoh=fileoh) #Normalized counts, cell density
            pbar1.update(1)
        pbar1.close()
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
    filename_massttest = r'C:\Users\listo\mass_ttests_obj.pkl'
    if os.path.isfile(filename_massttest):
        massttest_obj=mass_ttest.load(filename_massttest)
    else:
        massttest_obj=mass_ttest(atlas_json_file = r'C:\Users\listo\ara_ontology.json',
                        atlas_path=r'C:\Users\listo\ara_annotation_10um.tif',
                        drop_directory=r'C:\Users\listo\rabies_cort_cohort2_figures',
                        dataframe_path=r'C:\Users\listo\rabies_cort_cohort2_dataset.csv',
                        abs_min_val=-4,
                        abs_max_val=4)
        massttest_obj()
        massttest_obj.save(filename_massttest)

    # Run analysis on counts
    filename_counts = r'C:\Users\listo\total_counts_obj.pkl'
    if os.path.isfile(filename_counts):
        total_counts_obj=total_counts.load(filename_counts)
    else:
        total_counts_obj=total_counts(atlas_json_file = r'C:\Users\listo\ara_ontology.json',
                        atlas_path=r'C:\Users\listo\ara_annotation_10um.tif',
                        drop_directory=r'C:\Users\listo\rabies_cort_cohort2_figures',
                        dataframe_path=r'C:\Users\listo\rabies_cort_cohort2_dataset.csv',
                        abs_min_val=0,
                        abs_max_val=10)
        total_counts_obj()
        total_counts_obj.save(filename_counts)
