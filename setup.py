#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module name: setup.py
Description: Package configuration for BrainBeam
Author: David Estrin
Version: 1.0
Date: 11-14-2024
"""

from pathlib import Path

from setuptools import find_namespace_packages, setup


BASE_DIR = Path(__file__).resolve().parent
REQUIREMENTS_FILE = BASE_DIR / 'requirements.txt'


def read_requirements(file_path: Path = REQUIREMENTS_FILE):
    raw_requirements = file_path.read_bytes()
    decoded_requirements = None

    for encoding in ('utf-8-sig', 'utf-16', 'utf-16le'):
        try:
            candidate = raw_requirements.decode(encoding)
        except UnicodeDecodeError:
            continue

        if '\x00' in candidate:
            continue

        decoded_requirements = candidate
        break

    if decoded_requirements is None:
        raise UnicodeError(f'Unable to decode requirements file: {file_path}')

    requirements = []
    for line in decoded_requirements.splitlines():
        requirement = line.strip()
        if requirement and not requirement.startswith('#'):
            requirements.append(requirement)

    return list(dict.fromkeys(requirements))


setup(
    name='BrainBeam',
    version='0.1',
    packages=find_namespace_packages(include=['BrainBeam*']),
    install_requires=read_requirements(),
    author='David Estrin',
    author_email='',
    description='Brain Beam is used for light sheet analysis',
    url='https://github.com/DJESTRIN/BrainBeam',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.9',
)
