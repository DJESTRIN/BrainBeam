#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module name: setup.py
Description: Used to set up Sweet2Plus as a package
Author: David Estrin
Version: 1.0
Date: 11-14-2024
"""

from setuptools import setup, find_packages
import os

# Function to read and convert UTF-16LE requirements.txt to UTF-8
def read_requirements():
    file_path = 'requirements.txt'
    
    with open(file_path, 'rb') as f:
        content = f.read()
    
    try:
        # Try decoding the content as UTF-8
        requirements = content.decode('utf-8').splitlines()
        
    except UnicodeDecodeError:
        # If decoding as UTF-8 fails, decode as UTF-16LE and re-encode to UTF-8
        requirements = content.decode('utf-16le').splitlines()
        
        # Re-save the file with UTF-8 encoding
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(requirements))

        with open(file_path, 'rb') as f:
            content = f.read()
        requirements = content.decode('utf-8').splitlines()
    return requirements

requirements = read_requirements()

additional_packages = [
    'numpy',
    'matplotlib',
    'pandas',
    'ipdb',
    'seaborn',
    'scikit-learn',
    'tqdm']

requirements.extend(additional_packages)

setup(
    name='BrainBeam',
    version='0.1',
    packages=find_packages(),  # Automatically find subfolder1 and subfolder2 as packages.
    install_requires=requirements,
    author='David Estrin',
    author_email='',
    description='Brain Beam is used for light sheet analysis',
    url='https://github.com/DJESTRIN/BrainBeam',  # Replace with your repository URL.
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.7',
)
