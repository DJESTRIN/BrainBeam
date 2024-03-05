#!/bin/bash
input_dir=$1
cd $input_dir
folders=$(find $1 -type d)
array=( $folders )

for i in "${array[@]}"
do
	echo "$i"
	sbatch --job-name=delete --mem=200G --partition=scu-cpu,sackler-cpu --mail-type=BEGIN,END,FAIL --mail-user=dje4001@med.cornell.edu --wrap="rm -rfv '$i'"

done 
