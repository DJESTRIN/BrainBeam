#!/bin/bash
input=$1

cd "$input" || exit 1
mapfile -t failed_paths < <(du "$PWD" -h -d 2 --threshold=-5G | grep 'Ex_' | cut -f2-)

cd ~/lightsheet_cluster/ || exit 1

for output_stitch_path in "${failed_paths[@]}";
do

start_destripe_path=${output_stitch_path/stitched/destriped}
start_destripe_path=$start_destripe_path"/xml_placetiles.xml"
echo $start_destripe_path
echo $output_stitch_path

sbatch --job-name=placingtiles --mem=150G --partition=scu-gpu --gres=gpu:1 --mail-type=BEGIN,END,FAIL --mail-user=dje4001@med.cornell.edu --wrap="bash ./placetiles.sh '$start_destripe_path' '$output_stitch_path/'"

done
