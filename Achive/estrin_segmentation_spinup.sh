#!/bin/bash/
#Passed variables from previous script
code_directory=$1
scratch_directory=$2
store_finish_directory=$3

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
sbatch --job-name=split_cubes_for_ilastik --mem=300G --partition=scu-cpu --mail-type=BEGIN,END,FAIL --mail-user=dje4001@med.cornell.edu --wrap="bash ./estrin_split_cubes.sh '$TMP' '$scratch_directory'"

done

# Begin applying ilastik to the segments
sbatch --mem=5G --partition=scu-cpu --dependency=singleton --job-name=stitch_files --wrap="bash estrin_applyilastik_spinup.sh '$code_directory' '$scratch_directory' '$store_finish_directory'"


