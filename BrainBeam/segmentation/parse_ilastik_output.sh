#!/bin/bash

# Parse command line inputs
code_dir=$1
slice_folder=$2

# Get local numpy files if present
numpy_files=$( find $slice_folder -type f -name '*npz*' )

# Set up the environment
source ~/.bashrc
conda activate /home/fs01/dje4001/anaconda3/envs/spyder
cd $code_dir

# Loop over numpy files and run parse code
for file in $numpy_files; do
    echo $file
    python ./parse_ilastik_output.py --numpy_file_path $file

done
