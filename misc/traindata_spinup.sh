#!/bin/bash/
#Passed variables from previous script
code_directory=$1
scratch_directory=$2
store_finish_directory=$3

#Create output folder for training data
mkdir -p $store_finish_directory/training_data/


# Get a list of samples in stitched directory
samples=$(find $scratch_directory/lightsheet/stitched/ -maxdepth 1 -mindepth 1 -type d)

# Go to code directory
cd $code_directory

# Loop through samples to generate training data 
for i in $samples
do
	channels=$(find $i -maxdepth 1 -mindepth 1 -type d)
	sample_number=$(basename $i)

	#Loop through channels to generate training data
	for channel in $channels
	do
		channel_number=$(basename $channel)
		output_name=$store_finish_directory/training_data/$sample_number/$channel_number
		mkdir -p $output_name
		sbatch --mem=50G --partition=scu-cpu --wrap="bash estrin_grab_training_data.sh '$code_directory' '$channel' '$output_name'"
	done
done
