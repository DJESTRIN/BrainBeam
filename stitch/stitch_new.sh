#!/bin/bash

# Arguments
SEARCHPATH=$1
scratch_directory=$2
manual_override=${3:-false} # recalculate all files

# Environment setup
echo "Activate correct environment"
source ~/.bashrc
module load cuda
module load openmpi/5.0.1
module load ucx/1.11.2 libfabric/1.13.0
export USECUDA_X_NCC=1
conda activate /home/fs01/dje4001/anaconda3/envs/stitch
export LD_LIBRARY_PATH=/lib64:$LD_LIBRARY_PATH
pip install --no-cache-dir mpi4py

# Paths and directories
terastitcher_dir=/home/fs01/dje4001/Downloads/TeraStitcher-portable-1.11.10-Linux/
parastitcher=/home/fs01/dje4001/Downloads/TeraStitcher-portable-1.11.10-Linux/parastitcher.py
base_name=$(basename ${SEARCHPATH})
starting_directory=$PWD

# Input and output directories
tag1="lightsheet/destriped/"
input_base="${scratch_directory}${tag1}${base_name}/"
tag2="lightsheet/stitched/"
output="${scratch_directory}${tag2}${base_name}/"
mkdir -p $output
echo "This is the input directory: $input_base"
echo "This is the output directory: $output"

# Change to input directory
cd $input_base

# Stitching process
for sub_folder in ${input_base}*/; do
    cd $terastitcher_dir
    echo "This is the input directory: ${sub_folder}"

    # Determine if import file was created
    if [[ -e "${input}xml_import.xml" && "$manual_override" != "true" ]]; then
        echo "Import file already exists for this channel, skipping this step"
    else
        ./terastitcher --import --volin="$input" --projout="${input}xml_import.xml" --ref1=H --ref2=V --ref3=D --vxl1=1.83 --vxl2=1.83 --vxl3=2 --volin_plugin="TiledXY|2Dseries" --sparse_data
        chmod -R o+rwx "${input}xml_import.xml"
    fi 

        # From import get displcomp 
        if [[ -e "${input}xml_displcomp.xml" && "$manual_override" != "true" ]]; then
            echo "Displcomp file already exists for this channel, skipping this step"
        else
            mpirun -np 4 --oversubscribe python "$PARASTITCHER" -2 --projin="${input}xml_import.xml" --projout="${input}xml_displcomp" --subvoldim=600 --sV=25 --sH=25 --sD=0
        fi

        # Copy xml_displcomp to other channels
        for i in ${input_base}*/; do
            echo "Copying the xml_displcomp file to all channels"
            echo "This is the file we are copying: ${input}xml_displcomp.xml"
            echo "This is the place it is going: $i"
            rsync "${input}xml_displcomp.xml" "$i"
        done

        # From import get displcomp 
        if [[ -e "${input}xml_displproj.xml" && "$manual_override" != "true" ]]; then
            echo "Displproj file already exists for this channel, skipping this step"
        else
            ./terastitcher --displproj --projin="${input}xml_displcomp.xml" --projout=xml_displproj
        fi


        ./terastitcher --displthres --projin="${input}xml_displproj.xml" --projout=xml_displthres --threshold=0.5
        ./terastitcher --placetiles --projin="${input}xml_displthres.xml" --projout=xml_placetiles

        # Create output folder
        sf_basename=$(basename $input)
        mkdir -p "$output$sf_basename"
        mpirun -np 4 --oversubscribe python "$PARASTITCHER" -6 --projin="${input}xml_placetiles.xml" --volout="$output$sf_basename" --volout_plugin="TiledXY|2Dseries" --slicewidth=100000 --$
        
        let counter=counter+1
    else
        echo "Got to next part of loop"
        echo "This is the input directory: $input"

        ./terastitcher --displproj --projin="${input}xml_displcomp.xml" --projout="${input}xml_displproj"
        ./terastitcher --displthres --projin="${input}xml_displproj.xml" --projout="${input}xml_displthres" --threshold=0.5
        ./terastitcher --placetiles --projin="${input}xml_displthres.xml" --projout="${input}xml_placetiles"

        # Create output folder for this channel
        sf_basename=$(basename $input)
        mkdir -p "$output$sf_basename"

        # Merge files using GPU
        mpirun -np 4 --oversubscribe python "$PARASTITCHER" -6 --projin="${input}xml_placetiles.xml" --volout="$output$sf_basename" --volout_plugin="TiledXY|2Dseries" --slicewidth=100000 --$
        let counter++
    fi

    # Move images from subdirectories to main output folder
    cd "$output$sf_basename"
    find -name "*.tif*" -exec mv "{}" . \;
    rm -R -- */
done

exit


