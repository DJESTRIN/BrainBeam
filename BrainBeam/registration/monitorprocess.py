#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: monitorprocess.py
Description: 
Author: David Estrin
Date: 2024-008-15
Version: 1.0
"""
import pickle
import os
import shutil 
from pathlib import Path
import ipdb

def extract_path_info(path_oh):
    """ Copied from mulinoderegistration managepaths class
    Needed to copy due to circular import """
    # Get the subfolder
    parts = path_oh.strip('/').split('/')
    for part in parts:
        if "cage" in part.lower() and "animal" in part.lower():
            important_part = part
            break

    # Find the cage and subject information
    parts = important_part.strip('_').split('_')
    cage = None
    subject = None
    for part in parts:
        if "cage" in part.lower():
            cage = part.lower()
        if "animal" in part.lower():
            subject = part.lower()
    return cage, subject

def monitor(common_drop_directory, directory_file = "running_directories.pkl", currently_running=True,file_extensions=['jpg','gif']):
    """ The primary purpose of this function is to montior for file changes in given output directories. 
        Ex. search for new jpg images, copy them to communal directory and update their name so that they can easily downloaded via rsync  """
    
    if currently_running:
        if os.path.isfile(os.path.join(common_drop_directory, directory_file)):
            # Find directory file and open it
            print("Opening up the running output directories")
            with open(os.path.join(common_drop_directory,"running_directories.pkl"),"rb") as f:
                directories_list = pickle.load(f)

            # Double check path is real and exists
            Path(common_drop_directory).mkdir(parents=True, exist_ok=True)

            # Loop over drop direcectories from file
            for drop_directory in directories_list:

                print(f"Searching through {drop_directory}")
                
                # Loop over provided file types that we want to monitor. 
                for filetype in file_extensions:

                    # Loop over found files
                    for file in Path(drop_directory).glob(f'*.{filetype}'): 
                        
                        # Build output filename
                        ipdb.set_trace()
                        cage, subject = extract_path_info(file)
                        new_file_name = f"{cage}_{subject}_{file.name}"
                        output_file_oh = Path(common_drop_directory) / new_file_name

                        # Determin if file is new or if the time has changed
                        if not output_file_oh.exists() or (file.stat().st_mtime > output_file_oh.stat().st_mtime):
                            shutil.copy2(file, output_file_oh)
                            print(f"Copied: {file} to {output_file_oh}")

        else:
            print('Directory file was not found in given path')