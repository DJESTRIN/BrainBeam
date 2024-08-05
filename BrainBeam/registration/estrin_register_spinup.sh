#!/bin/bash
#Passed variables from previous script
code_directory=$1
scratch_directory=$2

# Create folder for terastitcher output
scratch_cloudreg=${scratch_directory}"lightsheet/cloudreg/"
scratch_registered=${scratch_directory}"lightsheet/registered/"
mkdir -p $scratch_registered

#Update sample list (in the case of any issues)
cd $code_directory

# Calculate precomputed volumes for each sample
counter=1
thresh=0
for sample in $scratch_cloudreg*/
do
	input=$sample"Ex_647_Em_680"
	output="${input/cloudreg/registered}"

	echo $input
	echo $output
	echo $counter

	if [ "$counter" -gt "$thresh" ];
	then
		echo $sample
		sbatch --job-name=reg_init --mem=300G --partition=scu-cpu --cpus-per-task=16 --mail-type=BEGIN,END,FAIL --mail-user=dje4001@med.cornell.edu --wrap="bash ~/lightsheet_cluster/estrin_register.sh $input $output"

	else
		echo 'skipping this brain'
	fi

counter=$((counter + 1))
done

