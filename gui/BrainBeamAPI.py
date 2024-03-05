""" BrainBeamAPI
The purpose of this script is to allow users to interface with back-end software via a simple programming interface. 
Designating --headless will trigger the API instead of the GUI. 
"""
class API():
    def __init__(self,command):
        self.command=command
    def copy_data(self):
        print('Dave')