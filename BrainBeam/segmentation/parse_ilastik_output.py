#Package dependencies
import os
import numpy as np
from pathlib import PurePath
from skimage.measure import regionprops as rp
from skimage.measure import label
import argparse
import pandas as pd

def parse_offsets(path):
    normalized_parts = PurePath(str(path).replace('\\', '/')).parts
    slice_name = next(part for part in normalized_parts if part.startswith('slice'))
    slice_index = normalized_parts.index(slice_name)

    if slice_index + 1 >= len(normalized_parts):
        raise ValueError(f'Could not determine cube directory from path: {path}')

    cube_name = normalized_parts[slice_index + 1]
    y_start, x_start = cube_name.split('_')
    z_start = slice_name.replace('slice', '', 1)
    return int(z_start), int(y_start), int(x_start)


def get_coordinates(path,threshold=0.92):
    """
    Inputs:
    path -- Full path to the ilastik numpy file
    threshold -- Threshold to be applied, default 0.92 

    Outputs:
    Saves a csv file containing coordinates of cells.
    """
    #load in segmentation 
    fileoh=np.load(path)
    largemat = fileoh['data']
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

    #rescale coordinates
    if points.size==0:
        return
    else:
        z_start, y_start, x_start = parse_offsets(path)
        points[:,0]+=z_start
        points[:,1]+=y_start
        points[:,2]+=x_start
        doh=pd.DataFrame({'x':points[:,2],'y':points[:,1],'z':points[:,0]})
    
        #Set up the output file
        outfile,_=os.path.splitext(path)
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




    
