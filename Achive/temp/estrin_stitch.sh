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
	echo here $input	
	#if [[ $counter -eq 0 ]]
	#then
	#	echo This is the input directory: $input
	#	
	#	./terastitcher --import --volin="$input" --projout=xml_import --ref1=H --ref2=V --ref3=D --vxl1=1.83 --vxl2=1.83 --vxl3=2 --volin_plugin="TiledXY|2Dseries" --sparse_data
	#	./terastitcher --displcompute --projin="${input}xml_import.xml" --projout="${input}xml_displcomp" --subvoldim=600 --sV=25 --sH=25 --sD=0
	#	chmod -R o+rwx "${input}xml_merging.xml"		
	#
	#	# Parrallel Alignment ==> This is the default, need to validate gpu is engaged
	#	#OLD VERSION OF COMMAND mpirun -n 2 -host $SLURM_JOB_NODELIST python "$PARASTITCHER" -2 --projin="${input}xml_import.xml" --projout="${input}xml_displcomp" --subvoldim=600 --sV=25 --sH=25 --sD=0
	#	#mpirun -np 4 --oversubscribe python "$PARASTITCHER" -2 --projin="${input}xml_import.xml" --projout="${input}xml_displcomp" --subvoldim=600 --sV=25 --sH=25 --sD=0
       	#	#chmod -R o+rwx "${input}xml_merging.xml"
	#	
	#	#Copy all displcompute files to other channels
	#	for i in $input_base*/;
	#	do
	#	
	#		echo copying the xml_displcomp file to all channels
	#		echo This is the file we are copying: ${input}xml_displcomp.xml
	#		echo This is the place it is going: $i
	#		rsync ${input}xml_displcomp.xml $i
	#	
	#	done
	#	
	#	./terastitcher --displproj --projin="${input}xml_displcomp.xml" --projout=xml_displproj
	#	./terastitcher --displthres --projin="${input}xml_displproj.xml" --projout=xml_displthres --threshold=0.5
	#	./terastitcher --placetiles --projin="${input}xml_displthres.xml" --projout=xml_placetiles
	#	
	#	#create an output folder
	#	sf_basename=$(basename $input)
	#	mkdir -p "$output$sf_basename"
	#	#mpirun -np 4 --oversubscribe python "$PARASTITCHER" -6 --projin="${input}xml_placetiles.xml" --volout="$output$sf_basename" --volout_plugin="TiledXY|2Dseries" --slicewidth=100000 --sliceheight=150000
	#	#OLD VERSION OF COMMAND mpiexec -n 2 --oversubscribe python "$PARASTITCHER" -6 --projin="${input}xml_placetiles.xml" --volout="$output$sf_basename" --volout_plugin="TiledXY|2Dseries" --slicewidth=100000 --sliceheight=150000
	#	
	#	# Merge files using CPU not gpu
	#	./terastitcher --merge --projin="${input}xml_placetiles.xml" --volout="$output$sub_folder" --volout_plugin="TiledXY|2Dseries" --slicewidth=100000 --sliceheight=150000
	#	let counter++
	if [[ $counter -gt 0 ]]
	then
		echo Got to next part of loop
		echo This is the input directory: $input
		
		#./terastitcher --displproj --projin="${input}xml_displcomp.xml" --projout="${input}xml_displproj"
                #./terastitcher --displthres --projin="${input}xml_displproj.xml" --projout="${input}xml_displthres" --threshold=0.5
                #./terastitcher --placetiles --projin="${input}xml_displthres.xml" --projout="${input}xml_placetiles"
		
		echo Finished placeing tiles	

		#create an output folder for this channel
		sf_basename=$(basename $input)
                mkdir -p "$output$sf_basename"
		echo "$output$sf_basename"

		# Merge files using GPU not CPU
		# OLD COMMAND mpiexec -n 2 -host $SLURM_JOB_NODELIST python "$PARASTITCHER" -6 --projin="${input}xml_placetiles.xml" --volout="$output$sf_basename" --volout_plugin="TiledXY|2Dseries" --slicewidth=100000 --sliceheight=150000
		#mpirun -np 4 --oversubscribe python "$PARASTITCHER" -6 --projin="${input}xml_placetiles.xml" --volout="$output$sf_basename" --volout_plugin="TiledXY|2Dseries" --slicewidth=100000 --sliceheight=150000

		echo "${input}xml_placetiles.xml"
		# Merge files using CPU not gpu
		./terastitcher --merge --projin="${input}xml_placetiles.xml" --volout="$output$sf_basename" --volout_plugin="TiledXY|2Dseries" --slicewidth=100000 --sliceheight=150000
	fi
	
	let counter++
	echo $counter
	#Move images from subdirectories into main output folder
	#cd "$output$sf_basename"
	#find -name "*.tif*" -exec mv "{}" . \;
	#rm -R -- */

done

#Exit code
exit
