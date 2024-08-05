#!/bin/bash
module load cuda
source ~/.bashrc
conda activate cloudreg

# bind the data input and output folders (two -B arguments) so that they are accessible within the container
mkdir -p /athena/listonlab/scratch/dje4001/lightsheet/cloudreg/
singularity shell -B /athena/listonlab/scratch/dje4001/lightsheet/stitched/20220905_17_43_29_CAGE3791032_ANIMAL02_VIRUSAAVRGDIOMCHERRY_TMTEXPERIMENTAL/Ex_488_Em_525/:/data/input -B /athena/listonlab/scratch/dje4001/lightsheet/cloudreg/:/data/output cloudreg_local.simg

# cd into the CloudReg folder
cd CloudReg

# run create_precomputed_volume with <input folder>, <voxel size>, <output folder>
python -m cloudreg.scripts.create_precomputed_volume /data/input 1.83 1.83 2 file:///data/output

cd ~/neuroglancer
python cors_webserver.py --directory /data/output

