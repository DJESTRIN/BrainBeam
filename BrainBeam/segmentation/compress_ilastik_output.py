#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: compress_ilastik_output.py
Description: 
Author: David Estrin
Date: 2024-08-28
Version: 1.0
"""

import os
import numpy as np
import argparse

def compress_numpy_files(root_dir):
    """
    Recursively finds all .npy files in the root directory, compresses them into .npz files,
    and deletes the original .npy file if compression was successful.
    """
    # Walk through the directory structure
    for dirpath, _, filenames in os.walk(root_dir):
        for file in filenames:
            # Only process .npy files
            if file.endswith('.npy'):
                file_path = os.path.join(dirpath, file)
                
                try:
                    # Load the original numpy file
                    data = np.load(file_path)

                    # Create the compressed file path
                    compressed_file_path = os.path.splitext(file_path)[0] + '.npz'

                    # Save as a compressed numpy file
                    np.savez_compressed(compressed_file_path, data=data)

                    # Verify that the compressed file exists
                    if os.path.exists(compressed_file_path):
                        # Delete the original .npy file
                        os.remove(file_path)
                        print(f"Compressed and removed: {file_path}")
                    else:
                        print(f"Failed to compress: {file_path}")

                except Exception as e:
                    print(f"Error processing {file_path}: {e}")

if __name__=='__main__':
    # Parse command line inputs
    parser=argparse.ArgumentParser()
    parser.add_argument('--input_dir',type=str,required=True)
    args=parser.parse_args()

    # Run compression on numpy files
    compress_numpy_files(args.input_dir)

