#!/bin/bash
#Passed variables from previous script
code_directory=$1
input_sample_directory=$2
output_sample_directory=$3


sbatch --job-name=registration --mem=200G --partition=scu-gpu,sackler-gpu --gres=gpu:2 --mail-type=BEGIN,END,FAIL --mail-user=dje4001@med.cornell.edu --wrap="bash ./estrin_register.sh $code_directory $channel $output"
		

