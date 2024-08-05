#!/bin/bash
# Split up stitched data into cubes. 
code_directory=$1
scratch_directory=$2

# Create folder for terastitcher output
scratch_stitch=${scratch_directory}"lightsheet/stitched/"
scratch_ilastik=${scratch_directory}"lightsheet/ilastik/"
mkdir -p $scratch_ilastik

#Update sample list (in the case of any issues)
cd $code_directory

# Stitch images using terastitcher
for i in $scratch_stitch*/
do
TMP=$(echo $i)
echo $TMP
sbatch --job-name=split_up_cubes --mem=200G --partition=scu-cpu  --mail-type=BEGIN,END,FAIL --mail-user=dje4001@med.cornell.edu --wrap="bash ./estrin_split_cubes.sh '$TMP' '$scratch_directory'" 

done

