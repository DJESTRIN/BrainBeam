#!/bin/bash
# Activate pystripe conda environemnt
code_directory=~/estrin_lightsheet/
scratch_directory=/athena/listonlab/scratch/dje4001/
store_directory=/athena/listonlab/store/dje4001/lightsheet/rabies/
cd $code_directory

## Todo: write a quick python script to continually update pending data

# Copy all pending data to the scratch drive
for i in $(cat $store_directorysubjectlist.txt)
do
TMP=$(echo $i)
sbatch --mem=64G --partition=scu-cpu --wrap="./copy.sh $TMP"
done
wait

#Zip data on scratch drive
cd $scratch_directory
now$(date +"%m_%d_%Y")
ZipFileName=lightsheet_backup_$now.zip
zip -r $ZipFileName $scratch_directorylightsheet_zip

# Send Zipped folder back to store
rsync -av $ZipFileName $store_directory/

# Send subjectlist to scratch directory
rync -av $store_directorysubjectlist.txt $scratch_directory

# TODO:	Insert python script replacing 0 byte files with empty images.

# Create folder	for destripe output
mkdir -p $scratch_directorydestriped/

# Destripe images
cd $code_directory
for i in $(cat $scratch_directorysubjectlist.txt)
do
TMP=$(echo $i)
sbatch --mem=64G --partition=scu-cpu --wrap="./estrin_destripe.sh $TMP"
done
wait

# Create folder	for terastitcher output
mkdir -p $scratch_directorystitched/

# Stitch images	using terastitcher
for i in $(cat $scratch_directorysubjectlist.txt)
do
TMP=$(echo $i)
sbatch --mem=64G --partition=scu-gpu --wrap="./estrin_stitch.sh $TMP"
done
wait

# Push everything back to storage
mkdir -p $store_directory/destriped/
mkdir -p $store_directory/stitched/
rsync -av $scratch_directorydestriped/ $store_directory/destriped/
rsync -av $scratch_directorystitched/ $store_directory/stiched/

echo "Remember to manually inspect data in storage and then manually delete data on scratch drive"


