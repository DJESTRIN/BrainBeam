# -*- coding: utf-8 -*-
"""
create projects
"""
from syglass import pyglass
import syglass as sy
import time
import os

#example="F:\\rabies_experiment_restain_training\\20221104_10_02_32_CAGE4094795_ANIMAL1_VIRUSRABIES_CORTEXPERIMENTAL\\Ex_647_Em_6800_syglass\\"
#first_image="F:\\rabies_experiment_restain_training\\20221104_10_02_32_CAGE4094795_ANIMAL1_VIRUSRABIES_CORTEXPERIMENTAL\\Ex_647_Em_6800\\453180_450330_051960.tiff"

def create_syglass_file(output_dir,output_name,first_image_dir):
    # create a project by specifing a path and the name of the project to be created. In this case, we'll call the project autoGenProject.
    project = pyglass.CreateProject(pyglass.path(output_dir), output_name)
    
    # create a DirectoryDescriptor to search a folder for TIFFs that match a pattern
    dd = pyglass.DirectoryDescription()
    
    # show the directoryDescriptor the first image of the set, and it will create a file list of matching slices
    dd.InspectByReferenceFile(first_image_dir)
    
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
    
Parent_dir="F:\\rabies_experiment_restain_training\\"
for root,dirs,files in os.walk(Parent_dir):
    if "syglass" in root:
        continue
    
    if "Ex" in root:        
        #generate project name
        _,_,animalname,basename=root.split("\\")
        finalname=animalname+basename+"syglass"
        
        #generate output_dir
        output=root+animalname+basename+"syglass"
        
        for file in files:
            first_file = root+ "\\" + file
            break
        print(output)
        print(basename)
        print(first_file)
        if os.path.exists(output):
            print("project already created")
        else:
            create_syglass_file(output,finalname,first_file)
        
#example="F:\\rabies_experiment_restain_training\\20221104_10_02_32_CAGE4094795_ANIMAL1_VIRUSRABIES_CORTEXPERIMENTAL\\Ex_647_Em_6805syglass\\Ex_647_Em_6805syglass\\Ex_647_Em_6805syglass.syg"
#project = sy.get_project(example)
# load the multi tracking points into a dict
#pts = project.get_counting_points()

