import syglass as sg
import numpy as np
import pandas as pd
import ipdb

def main(syglassfile,countfile):
    # Load syglass project
    project=sg.get_project(syglassfile)

    # Convert CSV to numpy array
    df=pd.read_csv(countfile)
    counts=df.to_numpy()

    # load the multi tracking points into a dict
    project.set_multitracking_points([]) #Erase previous points
    pts = project.get_counting_points()

    # Re-order coordinates into a list
    reordered=[]
    for i,coordinate in enumerate(counts):
        x,y,z=coordinate
        reordered.append(np.array([z,y,x]))

    # Convert list into a numpy array
    reordered=np.asarray(reordered)
    reordered.shape=(len(reordered),3) #set shape
    ipdb.set_trace()

    # Set pts
    pts['Orange']=reordered

    # set the projects new and updated multi tracking points
    project.set_counting_points(pts)

    # retrieve the updated points
    out = project.get_counting_points()
    return print('finished')


if __name__=='__main__':
    sygfile=r"C:\Users\listo\data\20231010_19_26_11_CAGE4467197_ANIMAL02_VIRUSRABIES_CORTEXPERIMENTAL_SEXMALE_syglass\20231010_19_26_11_CAGE4467197_ANIMAL02_VIRUSRABIES_CORTEXPERIMENTAL_SEXMALE_syglass.syg"
    countfile=r"C:\Users\listo\data\cell_counts.csv"
    main(syglassfile=sygfile,countfile=countfile)
