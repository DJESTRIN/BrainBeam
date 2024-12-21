#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: cellregistration.py
Description: The point of this algorithm is to:
    (1) Downsample stitched data to atlas size
    (2) Downsample cell coordinates to atlas size
    (3) Map cell coordinates to 3D mask where cells within same voxel are aggregated. 
        Ex, a voxel containing 2 cells equals 2.
    (4) Run registration for raw data as well as cellcountmask to atlas space
    (5) The final output will be a saved 3d numpy array for the registered brain and the cell counts. 
Author: David Estrin
Date: 2024-12-11
Version: 1.0
"""
from BrainBeam.cust_registration.registration import main as register
from BrainBeam.cust_registration.registration import cli_parser
from functools import wraps
import argparse

# Wrap the original cliparser
def extended_cliparser(original_cliparser):
    @wraps(original_cliparser)
    def wrapper():
        # Call the original cliparser to get its arguments
        args = original_cliparser()
        
        # Dynamically add a new input
        parser = argparse.ArgumentParser(description="Extended parser")
        parser.add_argument('--input2', type=str, help="Second input (added dynamically)")
        
        # Parse only the new arguments
        new_args, _ = parser.parse_known_args()
        
        # Merge the original args and new args
        for key, value in vars(new_args).items():
            setattr(args, key, value)
        
        return args
    return wrapper

