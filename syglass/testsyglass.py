# -*- coding: utf-8 -*-
"""
create projects
"""
from syglass import pyglass
import syglass as sy
import time

# create a project by specifing a path and the name of the project to be created. In this case, we'll call the project autoGenProject.
project = pyglass.CreateProject(pyglass.path("Z:\\vanillacontrol\\syglass_output"), "test1")

# create a DirectoryDescriptor to search a folder for TIFFs that match a pattern
dd = pyglass.DirectoryDescription()

# show the directoryDescriptor the first image of the set, and it will create a file list of matching slices
dd.InspectByReferenceFile("Z:\\vanillacontrol\\20240108_13_59_15_CAGE4422955_ANIMAL1316_STRAINFOSTRAP2XAI9TDTOMATO_SEXFEMALE_VANILLA\\Ex_647_Em_680\\411840_440190_000000.tif")

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
