#!/bin/bash

# Input command line arguments
SEARCHPATH=$1
scratch_directory=$2
manual_override=${3:-false} # recalculate all files

# Set up environment
echo "Activate correct environment"
source ~/.bashrc
module load cuda
module load openmpi/5.0.1
module load ucx/1.11.2 libfabric/1.13.0
export USECUDA_X_NCC=1
conda activate /home/fs01/dje4001/anaconda3/envs/stitch
export LD_LIBRARY_PATH=/lib64:$LD_LIBRARY_PATH
pip install --no-cache-dir mpi4py

# Set up paths and directories
terastitcher_dir=/home/fs01/dje4001/Downloads/TeraStitcher-portable-1.11.10-Linux/
parastitcher=/home/fs01/dje4001/Downloads/TeraStitcher-portable-1.11.10-Linux/parastitcher.py
base_name=$(basename ${SEARCHPATH})
starting_directory=$PWD

# Set up input and output directories
tag1="lightsheet/destriped/"
input_base="${scratch_directory}${tag1}${base_name}/"
tag2="lightsheet/stitched/"
output="${scratch_directory}${tag2}${base_name}/"
mkdir -p $output
echo "This is the input directory: $input_base"
echo "This is the output directory: $output"

# Change to input directory
cd $input_base
first_directory=true

# Stich all sub folders in main folder
for sub_folder in ${input_base}*/; do
    cd $terastitcher_dir
    echo "This is the input directory: ${sub_folder}"

    # Copy files from first folder to remaining folders
    # if [ "$first_directory" = false ]; then
    #     # Copy files over from first subdirectory
    #     for file in $files_to_copy; do
    #         cp "$file" "$sub_folder"
    #     done

    #     #Change contents inside file 
    #     files_to_edit=$(find "$sub_folder" -maxdepth 1 -type f -name "*.xml")
    #     current_basename=$(basename $sub_folder) 
    #     for file in $files_to_edit; do
    #         sed -i "s/$first_basename/$current_basename/g" $file
    #     done
    # fi

    # Determine if import file was created
    if [[ -e "${sub_folder}xml_import.xml" && "$manual_override" != "true" ]]; then
        echo "Import file already exists for this channel, skipping this step"
    else
        ./terastitcher --import --volin="${sub_folder}" --projout="${sub_folder}xml_import.xml" --ref1=H --ref2=V --ref3=D --vxl1=1.83 --vxl2=1.83 --vxl3=2 --volin_plugin="TiledXY|2Dseries" --sparse_data
    fi 

    # Determine if displcomp file was created
    if [[ -e "${sub_folder}xml_displcomp.xml" && "$manual_override" != "true" ]]; then
        echo "Displcomp file already exists for this channel, skipping this step"
    else
        srun --partition=scu-gpu \
            --ntasks=4 \
            --cpus-per-task=4 \
            --gres=gpu:2 \
            --mem=200G \
            --time=24:00:00 \
            --mpi=pmi2 python "$parastitcher" \
            -2 \
            --projin="${sub_folder}xml_import.xml" \
            --projout="${sub_folder}xml_displcomp.xml" \
            --subvoldim=600 \
            --sV=25 \
            --sH=25 \
            --sD=0
        
        if [ $? -eq 0 ]; then
            echo "Displcomp was successful, moving on to rest of stitch"
        else
            echo "Displcomp had an error, exiting code"
            exit 1
        fi
    fi

    # Determine if displproj file was created 
    if [[ -e "${sub_folder}xml_displproj.xml" && "$manual_override" != "true" ]]; then
        echo "Displproj file already exists for this channel, skipping this step"
    else
        ./terastitcher --displproj --projin="${sub_folder}xml_displcomp.xml" --projout="${sub_folder}xml_displproj.xml"
    fi

    # Determine if displproj file was created 
    if [[ -e "${sub_folder}xml_displproj.xml" && "$manual_override" != "true" ]]; then
        echo "Displproj file already exists for this channel, skipping this step"
    else
        ./terastitcher --displthres --projin="${sub_folder}xml_displproj.xml" --projout="${sub_folder}xml_displthres.xml" --threshold=0.5
    fi

    # Determine if xml_placetiles file was created 
    if [[ -e "${sub_folder}xml_placetiles.xml" && "$manual_override" != "true" ]]; then
        echo "Displproj file already exists for this channel, skipping this step"
    else
        ./terastitcher --placetiles --projin="${sub_folder}xml_displthres.xml" --projout="${sub_folder}xml_placetiles.xml"
    fi

    # Copy all files to remaining folders
    # if [ "$first_directory" = true ]; then
    #     find "$sub_folder" -maxdepth 1 -type f -name "*.xml" --exec chmod -R o+rwx {} \; # Change permissions on these files
    #     files_to_copy=$(find "$sub_folder" -maxdepth 1 -type f -name "*.xml")
    #     first_directory=false # set this to false for remaining directories
    #     first_basename=$(basename $sub_folder) 
    # fi

    # Output tiles to tiff stack
    sf_basename=$(basename $sub_folder) 
    mkdir -p "$output$sf_basename" # Create output folder
    convert_images=false
    if [[ -d "$output$sf_basename" && "$manual_override" != "true" ]]; then
        # Check if the directory contains files
        if [[ $(find "$output$sf_basename" -type f | wc -l) -gt 0 ]]; then
            echo "Output folder already exists and contains files. Therefore, we are skipping"
        else
            convert_images=true
        fi
    else
        convert_images=true 
    fi

    if [[ "$convert_images" == "true" ]]; then
        srun --partition=scu-gpu \
            --ntasks=4 \
            --cpus-per-task=4 \
            --gres=gpu:2 \
            --mem=200G \
            --time=24:00:00 \
            --mpi=pmi2 python "$parastitcher" \
            -6 \
            --projin="${sub_folder}xml_placetiles.xml" \
            --volout="$output$sf_basename" \
            --volout_plugin="TiledXY|2Dseries" \
            --slicewidth=100000 \
            --sliceheight=150000

        if [ $? -eq 0 ]; then
            echo "output conversion was successful, moving on to rest of stitch"
        else
            echo "Output conversion had an error, exiting code"
            exit 1
        fi
    fi 

    # Move images from subdirectories to main output folder
    find "$output$sf_basename" -type f -name "*.tif*" -exec mv {} "$output$sf_basename" \;
    find "$output$sf_basename" -mindepth 1 -maxdepth 1 -type d -exec rm -rfv {} \;
done

exit


