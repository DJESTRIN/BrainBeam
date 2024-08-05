#!/bin/bash
code_dir=$1
ilastik_input_dir=$2
ilastik_file=$3

cd $code_dir

# Get all slice folders in dir
slicesdirs=$( find $ilastik_input_dir -type d -name '*slice*' )

for slicefolder in $slicesdirs;
do

echo $slicefolder
sbatch --job-name=batch_ilastik --mem=50G --cpus-per-task=8 --partition=scu-cpu --mail-type=BEGIN,END,FAIL --mail-user=dje4001@med.cornell.edu --wrap="bash ./headless_ilastik.sh '$ilastik_file' '$slicefolder'"

done
