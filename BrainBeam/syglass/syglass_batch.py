# -*- coding: utf-8 -*-
"""
create projects
"""
from syglass import pyglass
import syglass as sy
import time
import os,glob
import argparse
from threading import Thread
import ipdb

class generate_syglass():
    def __init__(self,path,outpath):
        self.path=path
        self.outpath=outpath

    def __call__(self):
        self.search_for_channels()
        self.set_filename()
        self.get_first_image()
        self.create_syg_file()

    def search_for_channels(self):
        search_string=os.path.join(self.path,'**/Ex*')
        self.channels = glob.glob(search_string,recursive=True)

        #Parse out previously made syglass files
        temp=[]
        for channel in self.channels:
            if 'syglass' not in channel:
                temp.append(channel)
        self.channels=temp
    
    def set_filename(self):
        self.filenames=[]
        for channel in self.channels:
            chnloh = os.path.basename(channel)
            chnldir = os.path.dirname(channel)
            anoh = os.path.basename(chnldir)
            filename = f'{anoh}{chnloh}syglass'
            self.filenames.append(filename)

    def get_first_image(self):
        self.first_images=[]
        for j,channel in enumerate(self.channels):
            search_string=os.path.join(channel,'*.tif*')
            images=glob.glob(search_string)
            try:
                self.first_images.append(images[0])
            except:
                self.filenames[j]=None
                self.first_images.append(None)


    def create_syg_file(self):
        for j,channel in enumerate(self.channels):
            if self.filenames[j] is not None:
                project = pyglass.CreateProject(pyglass.path(self.outpath), self.filenames[j])
                dd = pyglass.DirectoryDescription()
                dd.InspectByReferenceFile(self.first_images[j])
                dataProvider = pyglass.OpenTIFFs(dd.GetFileList(), False)
                includedChannels = pyglass.IntList(range(dataProvider.GetChannelsCount()))
                dataProvider.SetIncludedChannels(includedChannels)
                cd = pyglass.ConversionDriver()
                cd.SetInput(dataProvider)
                cd.SetOutput(project)
                cd.StartAsynchronous()
                while cd.GetPercentage() != 100:
                        print(cd.GetPercentage())
                        time.sleep(1)
                print(f'Finished with channel named:\n {self.filenames[j]}')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument("--batch_folder",type=str)
    parser.add_argument("--syglass_drop",type=str,required=True)
    args=parser.parse_args()
    mainrun = generate_syglass(args.batch_folder,args.syglass_drop) 
    t1 = Thread(target=mainrun(), args=[])

