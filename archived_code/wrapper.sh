#!/bin/bash -l
#SBATCH --job-name=destripe_lightsheet_data
#SBATCH --nodes=5
#SBATCH --time=0-00:05:00
#SBATCH --mem=300GB
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=dje4001@med.cornell.edu
#SBATCH --output=destripe_lightsheet_data_%j.log

echo Please remember to start a screen session and activate the correct conda env before starting
### Destripe data based on a destriped log file
# Create scratch directory
scratch_dir = \athena\listonlab\scratch\dje4001\lightsheet_destripe\
mkdir -p ${scratch_dir}

# Go to light sheet data directory
store_dir = \athena\listonlab\store\dje4001\lightsheet\
cd ${store_dir}

for folder in */;do
	# Move data to scratch drive
	cp $folder ${scratch_dir}
	
	# Create output directory for destriping
	destripe_dir = ${scratch_dir}_destripe
	mkdir -p $destripe_dir
	echo Destriping will be dropped in $destripe_dir
	cp ${scratch_dir}\metadata.txt $destripe_dir\metadata.txt
	cp ${scratch_dir}\TileSettings.ini $destripe_dir\TileSettings.ini
	cp ${scratch_dir}\ASI_logging.txt $destripe_dir\ASI_logging.txt

	# Create output directory for zipping raw image data
	zip_filename = ${scratch_dir}_rawzipped
	mkdir -p $zipped_dir
	echo Raw data will be zipped into $zipped_dir
	zip -r $zip_filename\compressed.zip ${scratch_dir}

	# Start Destriping
	pystipe -i ${scratch_dir\$direc} -o ${} -s1 256 -s2 64 -n 24
	echo Destriping is complete for $folder
done 

#Stitch data based on stitched log file

#Cloudreg

# Delete the scratch directory and finish
#rm -rf ${scratch_directory}
exit 0

