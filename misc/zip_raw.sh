#!/bin/bash
input_directory=$1 #Directory of the sample on hand
output_directory=$2 #Directory for the output of the zipped sample. 
scratch_directory=$3

# print everything for slurm output
echo This is the input: $input_directory
echo This is the output where data will be sent: $output_directory

cd $scratch_directory
tag=".zip"
base_name=$(basename input_directory)
zip_filename="$base_name$tag"

echo This is the zip file name: $zip_filename

#Zip the raw data
echo zipping the data now. This might take a while.
zip -r $zip_filename $input_directory

# Send Zipped folder back to store
echo Sending the zipped file back to storage.
rsync -av $zip_fileName $store_finish_directory


