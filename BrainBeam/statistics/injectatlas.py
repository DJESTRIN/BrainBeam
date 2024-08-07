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
        for sn in tqdm.tqdm(range(1,self.atlas_stack.shape[2])):
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
                            new_value=-1
                        else:
                            new_value=1
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
        return injected_slices

    def plot_atlas(self,stack,reference_stack,real_reference_stack,add_scalebar=True, filename = r'C:\Users\listo\example.jpg'):
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
