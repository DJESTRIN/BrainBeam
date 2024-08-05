#!/bin/bash
input=$1
scratch_directory=$2

#Set up input and output
base_name=$(basename ${input})
echo Base name = ${base_name}
tag=lightsheet/ilastik/

# Set up output root folder
root_output="$scratch_directory$tag$base_name"
mkdir -p $root_output

for channel_input in $input*/
do

	base_channel_name=$(basename ${channel_input})
	channel_output="$scratch_directory$tag$base_name/$base_channel_name"
	mkdir -p $channel_output

	# Seperate stitched images into cubes
	source ~/.bashrc
	conda activate ~/anaconda3/envs/regular
	python ~/lightsheet_cluster/divide_for_segmentation.py --input_dir $channel_input --output_dir $channel_output

done

exit
