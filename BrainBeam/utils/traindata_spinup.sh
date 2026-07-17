#!/bin/bash
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <code_directory> <scratch_directory> <store_finish_directory>"
    exit 1
fi

#Passed variables from previous script
code_directory=$1
scratch_directory=$2
store_finish_directory=$3
worker_script="$code_directory/BrainBeam/image_manipulations/grab_training_data.sh"

#Create output folder for training data
mkdir -p "$store_finish_directory/training_data/"

# Go to code directory
cd "$code_directory" || exit 1

if [ ! -f "$worker_script" ]; then
    echo "Error: Training data worker script not found at $worker_script"
    exit 1
fi

# Loop through samples to generate training data 
find "$scratch_directory/lightsheet/stitched/" -maxdepth 1 -mindepth 1 -type d -print0 | while IFS= read -r -d '' sample
do
	sample_number=$(basename "$sample")

	#Loop through channels to generate training data
	find "$sample" -maxdepth 1 -mindepth 1 -type d -print0 | while IFS= read -r -d '' channel
	do
		channel_number=$(basename "$channel")
		output_name="$store_finish_directory/training_data/$sample_number/$channel_number"
		mkdir -p "$output_name"
		sbatch --mem=50G --partition=scu-cpu --wrap="bash '$worker_script' '$code_directory' '$channel' '$output_name'"
	done
done
