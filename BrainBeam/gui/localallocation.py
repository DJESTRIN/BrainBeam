#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: localallocation.py
Description: 
Author: David Estrin
Date: 2025-02-11
Version: 1.0
"""
import os
import glob
import multiprocessing
import subprocess
import platform

def run_command(folder, command_template):
    system = platform.system()
    command = command_template.format(folder=folder)

    if system == "Windows":
        shell_executable = None  
    else:
        shell_executable = "/bin/bash" 

    subprocess.run(command, shell=True, executable=shell_executable, check=True)

def run_in_parallel(base_dir, command_template, num_workers=None):
    folders = glob.glob(os.path.join(base_dir, "*", "*Ex*"))

    # Default to half of available CPUs
    if num_workers is None:
        cpu_count = os.cpu_count() or 1
        num_workers = max(1, cpu_count // 2)

    # Run commands in parallel
    with multiprocessing.Pool(num_workers) as pool:
        pool.starmap(run_command, [(folder, command_template) for folder in folders])

if __name__ == "__main__":
    base_dir = os.path.expanduser("~/path/to/data")  # Change to your data directory

    # Define the command template with {folder} as a placeholder
    command_template = "source ~/.bashrc && conda activate ~/anaconda3/envs/regular && python script.py --input_dir {folder}"

    run_in_parallel(base_dir, command_template)
