#Package dependencies
import ipdb
import numpy as np
import os, glob
from skimage.measure import regionprops as rp
from skimage.measure import label
import matplotlib.pyplot as plt
from tqdm import tqdm
import argparse
import pandas as pd

def get_coordinates(path,threshold=0.92):
    """
    Inputs:
    path -- Full path to the ilastik numpy file
    threshold -- Threshold to be applied, default 0.92 

    Outputs:
    Saves a csv file containing coordinates of cells.
    """
    #load in segmentation 
    largemat=np.load(path)
    cellbodies=np.squeeze(largemat[:,:,:,2])
    cellbodies_copy=np.copy(cellbodies)

    #Threshold image
    cellbodies_copy[np.where(cellbodies>threshold)]=1
    cellbodies_copy[np.where(cellbodies<threshold)]=0

    #Group similar values
    labels=label(cellbodies_copy)
    regions=rp(labels)

    #Get coordinates of proposed point
    points=[]
    for region in regions:
        points.append(region.centroid)

    points=np.asarray(points)

    # Parse path name to update coordinate data
    _,newpath=path.split('slice')
    newpath,_=newpath.split('/image')
    z_start,xy_start=newpath.split('/')
    y_start,x_start=xy_start.split('_')
    
    #rescale coordinates
    if points.size==0:
        return
    else:
        points[:,0]+=int(x_start)
        points[:,1]+=int(y_start)
        points[:,2]+=int(z_start)
        doh=pd.DataFrame({'x':points[:,0],'y':points[:,1],'z':points[:,2]})
    
        #Set up the output file
        outfile,_=path.split('.')
        outfile+='.csv'
        
        #Save dataframe to csv file
        doh.to_csv(outfile,index=False)
        print(outfile)
    return


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--numpy_file_path",type=str)
    args = parser.parse_args()
    get_coordinates(path=args.numpy_file_path,threshold=0.92)




    
