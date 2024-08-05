#!/bin/bash
input=$1

cd $input
failed_paths=$( du $PWD -h -d 2 --threshold=-5G | awk '{print $2}' | grep 'Ex_' )

cd ~/lightsheet_cluster/

for output_stitch_path in $failed_paths;
do

start_destripe_path=${output_stitch_path/stitched/destriped}
start_destripe_path=$start_destripe_path"/xml_placetiles.xml"
echo $start_destripe_path
echo $output_stitch_path

sbatch --job-name=placingtiles --mem=150G --partition=scu-gpu --gres=gpu:1 --mail-type=BEGIN,END,FAIL --mail-user=dje4001@med.cornell.edu --wrap="bash ./placetiles.sh '$start_destripe_path' '$output_stitch_path/'"

done
