#!/bin/bash
code_directory=$1
sample_directory=$2
output_directory=$3

source ~/.bashrc
conda activate cell
module load cuda

cd $code_directory
python ./cellsegmentation.py --lifecanvas_code_directory /home/dje4001/LIGHTSHEET_CLUSTER/SA_files/ --input_dir $sample_directory --output_dir $output_directory

#Move everything to output directory. Oddly cellsegmentation code does not do this. 
cd $sample_directory
find -name "*.jpg" -exec mv "{}" . $output_directory ';'
find -name "*.pkl" -exec mv "{}" . $output_directory ';'
find -name "*.json" -exec mv "{}" . $output_directory ';'
cd $code_directory
