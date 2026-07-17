""" BrainBeam
The primary script for running the BrainBeam pipeline 
"""
from BrainBeamBase import BrainBeamGuiBase
from BrainBeamCLI import API
import argparse










if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--CopyData', action='store_true')
    args=parser.parse_args()
    if args.headless:
        api_oh=API()

    else:
        gui_oh=BrainBeamGuiBase()
        gui_oh()