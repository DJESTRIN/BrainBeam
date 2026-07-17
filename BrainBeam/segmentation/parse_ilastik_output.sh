#!/bin/bash

# Parse command line inputs
code_dir=$1
slice_folder=$2

# Set up the environment
source ~/.bashrc
conda activate /home/fs01/dje4001/anaconda3/envs/spyder
cd "$code_dir"

# Loop over numpy files and run parse code
while IFS= read -r -d '' file; do
    echo "$file"
    python ./parse_ilastik_output.py --numpy_file_path "$file"
done < <(find "$slice_folder" -type f -name '*.npz' -print0)
