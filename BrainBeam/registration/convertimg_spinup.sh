#!/bin/bash
code_dir=$1
inputdir=$2

img_files=$( find $inputdir -type f -name '*target.img*' )
echo $img_files

cd $code_dir

for sample in $img_files;
do
echo $sample
output=$( dirname $sample )
output=$output"/tiffsequence/"
echo $output
sbatch --job-name=convertatlas --mem=100G --partition=scu-cpu --mail-type=BEGIN,END,FAIL --mail-user=dje4001@med.cornell.edu --wrap="bash ./convert_img.sh '$sample' '$output'"

done
