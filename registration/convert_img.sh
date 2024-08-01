#!/bin/bash
input=$1
output=$2
source ~/.bashrc
conda activate /home/fs01/dje4001/anaconda3/envs/spyder
python ~/lightsheet_cluster/convert_image.py --input_image_path $input --output_path $output --mode nearest
