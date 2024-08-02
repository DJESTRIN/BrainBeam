""" BrainBeam
The primary script for running the BrainBeam pipeline 
"""
from BrainBeamBase import BrainBeamGuiBase
#from gui.BrainBeamCLI import API
import argparse










if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--headless',required=False,default=False)
    parser.add_argument('--CopyData',required=False,default=False)
    args=parser.parse_args()
    if args.headless:
        api_oh=API()

    else:
        gui_oh=BrainBeamGuiBase()
        gui_oh()