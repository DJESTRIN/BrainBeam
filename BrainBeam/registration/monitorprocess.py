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

def monitor(common_drop_directory, directory_file = "running_directories.pkl", currently_running=True,file_extensions=['jpg','gif']):
    if currently_running:
        if os.path.isfile(os.path.join(common_drop_directory, directory_file)):
            # Find directory file and open it
            with open(os.path.join(common_drop_directory,"running_directories.pkl"),"wb") as f:
                directories_list = pickle.load(f)


            # Double check path is real and exists
            Path(common_drop_directory).mkdir(parents=True, exist_ok=True)
            
            # Loop over drop direcectories from file
            for drop_directory in directories_list:

                # Loop over provided file types that we want to monitor. 
                for filetype in file_extensions:

                    # Loop over found files
                    for file in Path(drop_directory).glob(f'*.{filetype}'): 
                        
                        # Build output filename
                        output_file_oh = Path(common_drop_directory) / file.name

                        if not output_file_oh.exists() or (file.stat().st_mtime > output_file_oh.stat().st_mtime):
                            shutil.copy2(file, output_file_oh)
                            print(f"Copied: {file} to {dest_file}")

        else:
            print('Directory file was not foundin given path')


    # Move data from drop folders to commmon directory
        

# (12) Run script that continously monitors output directory
#     (a) Copies images over to common directory and renames them, making sure they have cage and subject ID in name ...
