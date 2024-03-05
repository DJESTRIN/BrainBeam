#!/bin/bash
SEARCHPATH=$1
scratch_directory=$2 

echo Activate correct environment
source ~/.bashrc
module load cuda
export USECUDA_X_NCC=1
conda activate stitch
#PARASTITCHER=/home/dje4001/TeraStitcher-portable-1.11.10-Linux/pyscripts/Parastitcher.py
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
	#cd ~/TeraStitcher-portable-1.11.10-Linux/
	input="$sub_folder"
	
	if [[ $counter -eq 0 ]]
	then
		echo This is the input directory: $input
		
		terastitcher --import --volin="$input" --projout=xml_import --ref1=H --ref2=V --ref3=D --vxl1=1.83 --vxl2=1.83 --vxl3=2 --volin_plugin="TiledXY|2Dseries" --sparse_data
		terastitcher --displcompute --projin="${input}xml_import.xml" --projout="${input}xml_displcomp" --subvoldim=600 --sV=25 --sH=25 --sD=0
		chmod -R o+rwx "${input}xml_merging.xml"		

		# Parrallel Alignment ==> This is the default, need to validate gpu is engaged
		# mpiexec -n 2 -host $SLURM_JOB_NODELIST python "$PARASTITCHER" -2 --projin="${input}xml_import.xml" --projout="${input}xml_displcomp" --subvoldim=600 --sV=25 --sH=25 --sD=0

	
		
		#Copy all displcompute files to other channels
		for i in $input_base*/;
		do
		
			echo copying the xml_displcomp file to all channels
			echo This is the file we are copying: ${input}xml_displcomp.xml
			echo This is the place it is going: $i
			rsync ${input}xml_displcomp.xml $i
		
		done
		
		terastitcher --displproj --projin="${input}xml_displcomp.xml" --projout=xml_displproj
		terastitcher --displthres --projin="${input}xml_displproj.xml" --projout=xml_displthres --threshold=0.5
		terastitcher --placetiles --projin="${input}xml_displthres.xml" --projout=xml_placetiles
		
		#create an output folder
		sf_basename=$(basename $input)
		mkdir -p "$output$sf_basename"
		#terastitcher --projin "${input}xml_placetiles.xml" --volout "$output$sf_basename" --volout_plugin "TiledXY|2Dseries" --slicewidth 100000 --sliceheight 150000
		
		# Merge files using CPU not gpu
		terastitcher --merge --projin="${input}xml_placetiles.xml" --volout="$output$sub_folder" --volout_plugin="TiledXY|2Dseries" --slicewidth=100000 --sliceheight=150000
		let counter=counter+1
	else
		echo Got to next part of loop
		echo This is the input directory: $input
		
		terastitcher --displproj --projin="${input}xml_displcomp.xml" --projout="${input}xml_displproj"
                terastitcher --displthres --projin="${input}xml_displproj.xml" --projout="${input}xml_displthres" --threshold=0.5
                terastitcher --placetiles --projin="${input}xml_displthres.xml" --projout="${input}xml_placetiles"
		
		#create an output folder for this channel
		sf_basename=$(basename $input)
                mkdir -p "$output$sf_basename"
		
		# Merge files using GPU not CPU
		#mpiexec -n 2 -host $SLURM_JOB_NODELIST python "$PARASTITCHER" -6 --projin="${input}xml_placetiles.xml" --volout="$output$sf_basename" --volout_plugin="TiledXY|2Dseries" --slicewidth=100000 --sliceheight=150000
		
		# Merge files using CPU not gpu
		terastitcher --merge --projin="$input/xml_placetiles.xml" --volout="$output$sub_folder" --volout_plugin="TiledXY|2Dseries" --slicewidth=100000 --sliceheight=150000
		let counter++

	fi
	
	#Move images from subdirectories into main output folder
	cd "$output$sf_basename"
	find -name "*.tif*" -exec mv "{}" . \;
	rm -R -- */

done

#Exit code
exit
