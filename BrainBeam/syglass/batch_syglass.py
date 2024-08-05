# -*- coding: utf-8 -*-
""" batch create syglass files
"""
import argparse
from syglass import pyglass
import syglass as sy
import time
import os,glob

def main(direct_oh):
    if direct_oh[-1:]!='/':
        output=direct_oh+"_syglass_output"
        bn=os.path.basename(output)
        dn=os.path.dirname(output)
        
        #Find first image
        FI=glob.glob(direct_oh+'/*.tif*')
    else:
        output=direct_oh[-1:]+"_syglass_output"
        bn=os.path.basename(output)
        dn=os.path.dirname(output)
        
        #Find first image
        FI=glob.glob(direct_oh+'*.tif*')
    
    if len(FI)<1:
        return print('did not have first tif')
        
    # create a project by specifing a path and the name of the project to be created. In this case, we'll call the project autoGenProject.
    project = pyglass.CreateProject(pyglass.path(dn), bn)
    
    # create a DirectoryDescriptor to search a folder for TIFFs that match a pattern
    dd = pyglass.DirectoryDescription()
    
    # show the directoryDescriptor the first image of the set, and it will create a file list of matching slices
    print(direct_oh)
    print(FI[0])
    dd.InspectByReferenceFile(FI[0])
    
    # create a DataProvider to the dataProvider the file list
    dataProvider = pyglass.OpenTIFFs(dd.GetFileList(), False)
    
    # indicate which channels to include; in this case, all channels from the file
    includedChannels = pyglass.IntList(range(dataProvider.GetChannelsCount()))
    dataProvider.SetIncludedChannels(includedChannels)
    
    # spawn a ConversionDriver to convert the data
    cd = pyglass.ConversionDriver()
    
    # set the ConversionDriver input to the data provider
    cd.SetInput(dataProvider)
    
    # set the ConversionDriver output to the project previously created
    cd.SetOutput(project)
    
    # start the job!
    cd.StartAsynchronous()
    
    # report progress
    while cd.GetPercentage() != 100:
            print(cd.GetPercentage())
            time.sleep(1)
    print("Finished!")

parser=argparse.ArgumentParser()
parser.add_argument("--input",type=str,required=True)


if __name__=='__main__':
    args=parser.parse_args()
    if 'syglass_output' in args.input: 
        print('skip')
    else:
        main(args.input)

    
    #output directory is same as input directory but says _syglassoutput