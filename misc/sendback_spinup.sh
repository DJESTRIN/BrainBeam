#!/bin/bash
input_dir=$1
output_foldername=$2/$3

cd $input_dir
samples=$(find $input_dir -maxdepth 1 -mindepth 1 -type d)

# Move all sample data to storage
for i in $samples
do 
TMP=$(echo $i)
echo $TMP
sample_name=$(basename $TMP)
sbatch --job-name=store_files --mem=100G --partition=scu-cpu,sackler-cpu --mail-type=BEGIN,END,FAIL --mail-user=dje4001@med.cornell.edu --wrap="bash /home/dje4001/lightsheet_cluster/estrin_sendback.sh '$TMP' '$sample_name' '$output_foldername'"

done 
