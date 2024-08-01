#!/bin/bash
slice_folder=$1
numpy_files=$( find $slice_folder -type f -name '*npy*' )
source ~/.bashrc
conda activate /home/fs01/dje4001/anaconda3/envs/spyder

for file in $numpy_files;
do
echo $file
python ~/lightsheet_cluster/parse_ilastik_output.py --numpy_file_path $file

done
