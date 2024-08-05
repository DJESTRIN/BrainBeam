#!/bin/bash
#Passed variables from previous script
code_directory=$1
scratch_directory=$2
store_finish_directory=$3

scratch_stitch=${scratch_directory}"lightsheet/stitched/"

#Update sample list (in the case of any issues)
cd $code_directory

# Run Cell Segmentation for each sample
for sample in $scratch_stitch*/
do
        TMP=$(echo $sample)
        echo $TMP
        for channel in $sample*/
        do
        	echo $channel
		second="segmented"
		output=${channel/"stitched"/$second}
		echo $output
		mkdir -p $output
        	sbatch --job-name=cellsegmentation --mem=500G --partition=sackler-gpu --gres=gpu:2 --mail-type=BEGIN,END,FAIL --mail-user=dje4001@med.cornell.edu --wrap="bash ./estrin_cellsegment.sh $code_directory $channel $output"
        done
done
exit


