#!/bin/bash
#Passed variables from previous script
code_directory=/home/dje4001/lightsheet_cluster
scratch_directory=$2
store_finish_directory=$3


channel=/athena/listonlab/store/dje4001/lightsheet/rabies/stitched/20220925_12_49_48_CAGE3752774_ANIMAL04_VIRUSRABIES_CORTEXPERIMENTAL/20220925_12_49_48_CAGE3752774_ANIMAL04_VIRUSRABIES_CORTEXPERIMENTAL/Ex_647_Em_680

scratch_stitch=${scratch_directory}"lightsheet/stitched/"

#Update sample list (in the case of any issues)
cd $code_directory

sbatch --job-name=cellsegmentation --mem=200G --partition=scu-gpu,sackler-gpu --gres=gpu:1 --mail-type=BEGIN,END,FAIL --mail-user=dje4001@med.cornell.edu --wrap="bash ./estrin_cellsegment.sh $channel $code_directory"


