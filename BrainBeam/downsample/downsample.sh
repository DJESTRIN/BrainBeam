#!/bin/bash
source ~/.bashrc
conda activate spyder-env
python /home/dje4001/lightsheet_cluster/downsample_script.py --input_path $1 --output_path $2

