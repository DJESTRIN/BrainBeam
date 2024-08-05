#!/bin/bash/
code_directory=$1
TMP=$2
source ~/.bashrc
conda activate regular
echo $TMP
echo $code_directory
output="${TMP/raw/converted}"
echo $output
mkdir -p $output
python $code_directory/convert_to_tiff.py --input_directory $TMP --output_directory $TMP
