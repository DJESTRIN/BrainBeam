#!/bin/bash
cd ~/CloudReg
#python -m cloudreg.scripts.create_precomputed_volume /data/input 1.83 1.83 2 file:///data/output --num_procs 24


python -m cloudreg.scripts.create_precomputed_volumes --input_parent_dir /data/input  --local_output_parent_dir "precomputed://file:///data/output" --voxel_size 1.83 1.83 2 --num_procs 100 --resample_iso False

#python -m cloudreg.scripts.create_precomputed_volume /athena/listonlab/scratch/dje4001/lightsheet/stitched/brain1/channel1/ 1.83 1.83 2 file:///athena/listonlab/scratch/dje4001/lightsheet/cloudreg/brain1/channel1/  --num_procs 24

