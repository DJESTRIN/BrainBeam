#!/bin/bash
# Parse command line inputs
code_dir=$1
ilastik_input_dir=$2
ilastik_file=$3

# Go to code directory
cd $code_dir

# Get all slice folders in dir
slicesdirs=$( find $ilastik_input_dir -type d -name '*slice*' )

# Loop over slice folders and pass to ilastik bash script
for slicefolder in $slicesdirs; do
    echo $slicefolder

done

exit 
