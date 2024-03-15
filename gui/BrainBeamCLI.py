""" BrainBeamAPI
The purpose of this script is to allow users to interface with back-end software via a simple programming interface. 
Designating --headless will trigger the API instead of the GUI. 
"""
import subprocess as sp
import os


class DigestData():
    def __init__(self):
        self.wd=os.getcwd()

    def directorytype(self):
        #Batch
        #single sample
        #neither
        self.dirflag='batch'
    
    def computertype(self):
        self.comflag='slurm'
        #self.compflag='local'
        #self.compflag='aws'

    def show_progress(self):


class CLI(DigestData):
    def copy(self):

    def move(self):

    def compress(self):

    def decompress(self):

    def convert(self):

    def denoise(self):

    def stitch(self):
        if self.dirflag=='batch':
            coh=f'bash {self.wd}/stitch/stitch_spinup.sh {self.wd} {}'

    def neuroglancer(self):

    def serve_to_neuroglancer(self):

    def register(self):

    def segmentation(self):

    def count(self):

    def custom(self):




if __name__=='__main__':
