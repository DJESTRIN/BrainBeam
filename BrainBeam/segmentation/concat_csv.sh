#!/bin/bash
subfolder=$1
source ~/.bashrc
conda activate ~/anaconda3/envs/regular
python ./concat_csv.py  --input_dir $subfolder