#!/bin/bash
#Passed variables from previous script
code_directory=$1
scratch_directory=$2
store_finish_directory=$3

# contrasted data no longer needed. Send back to storage
bash /home/dje4001/lightsheet_cluster/estrin_sendback_spinup.sh $scratch_directory/lightsheet/autocontrast/ $store_finish_directory autocontrast

# Create folder for downsample output
scratch_stitch=${scratch_directory}"lightsheet/stitched/"
scratch_downsampled=${scratch_directory}"lightsheet/downsampled/"
mkdir -p $scratch_downsampled

#Update sample list (in the case of any issues)
cd $code_directory

# Calculate precomputed volumes for each sample
for sample in $scratch_stitch*/
do
	for channel in $sample*/
	do
		echo $channel
		second="downsampled"
		output=${channel/"stitched"/$second}
		echo $output
		mkdir -p $output
		sbatch --job-name=downsample --mem=200G --partition=sackler-cpu,scu-cpu --mail-type=BEGIN,END,FAIL --mail-user=dje4001@med.cornell.edu --wrap="bash ./downsample.sh '$channel' '$output'"
	
	done
done

# downsample data can be sent to storage
sbatch --mem=5G --partition=scu-cpu --dependency=singleton --job-name=downsample --wrap="bash /home/dje4001/lightsheet_cluster/estrin_sendback_spinup.sh $scratch_directory/lightsheet/downsampled/ $store_finish_directory downsampled"
exit


