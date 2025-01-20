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

# Open requirements file and save to lsit
with open('requirements.txt','r', encoding='utf-8') as f:
    requirements = f.read().splitlines()

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
