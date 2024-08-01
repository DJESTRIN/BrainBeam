#!/bin/bash
SEARCHPATH=$1
scratch_directory=$2

echo Activate correct environment
source ~/.bashrc
module load cuda
module load openmpi/5.0.1
module load ucx/1.11.2  libfabric/1.13.0
export USECUDA_X_NCC=1
conda activate /home/fs01/dje4001/anaconda3/envs/stitch
#export LD_LIBRARY_PATH=/lib64:$LD_LIBRARY_PATH
#pip install --no-cache-dir mpi4py
PARASTITCHER=/home/fs01/dje4001/Downloads/TeraStitcher-portable-1.11.10-Linux/parastitcher.py
base_name=$(basename ${SEARCHPATH})
starting_directory=$PWD

# Create input and output folders
tag1=lightsheet/destriped/
input_base="$scratch_directory$tag1$base_name/"
tag2=lightsheet/stitched/
output="$scratch_directory$tag2$base_name/"
mkdir -p $output
echo This is the input directory: $input_base
echo This is the output directory: $output


#Get subfolders of input directory
cd $input_base

#Stitch based on first channel. This will need to change in the future to a user input.
counter=0
for sub_folder in $input_base*/;
do
        # Call terastitcher
        cd /home/fs01/dje4001/Downloads/TeraStitcher-portable-1.11.10-Linux/
        input="$sub_folder"

        if [[ $counter -eq 0 ]]
        then
	echo "${input}xml_placetiles.xml"
	chnl=$(basename $sub_folder)
	echo "$output$chnl"
	./terastitcher --merge --projin="${input}xml_placetiles.xml" --volout="$output$chnl" --volout_plugin="TiledXY|2Dseries" --slicewidth=100000 --sliceheight=150000
                let counter=counter+1
 fi

        #Move images from subdirectories into main output folder
        cd "$output$chnl"
        find -name "*.tif*" -exec mv "{}" . \;
        rm -R -- */

done

#Exit code
exit

