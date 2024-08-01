#!/bin/bash
project_file=$1
inputdir=$2
cd $inputdir
subdirs=$( find $PWD -type d -name '*_*' )

for sd in $subdirs;
do

npfile=$( find $sd -type f -name '*npy*' )

if [ -z "${npfile}" ];
then
	string="/image*.tiff"
	found_stack="$sd$string"
	echo "$found_stack"
	cd ~/Downloads/ilastik-1.4.0-Linux/

	./run_ilastik.sh --headless --project=$project_file \
		--output_format=numpy --stack_along="z" "$found_stack"
else
	echo "This path had a numpy file"
	echo $sd
fi

done
