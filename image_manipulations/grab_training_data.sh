#!/bin/bash/
source ~/.bashrc
conda activate spyder-env
cd $1
python grab_images.py --input_path $2 --output_path $3
