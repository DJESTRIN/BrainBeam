#!/bin/bash

# Parse command line inputs
code_dir=$1
slice_dir=$2

source ~/.bashrc
conda activate /home/fs01/dje4001/anaconda3/envs/regular

cd $code_dir
python ./compress_ilastik_output.py --input_dir $slice_dir
