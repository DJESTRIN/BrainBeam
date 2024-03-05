#!/bin/bash
# This script will initiate a singularity session where a precomputed volume will be calculated
sample_oh=$1 #full directory to stitched data ==> Input should be enitre sample
scratch_directory=$2
module load cuda
source ~/.bashrc
conda activate cloudreg

# Create cloud reg output on scratch (or double check) 
tag=lightsheet/cloudreg/
cloudreg_drop="$scratch_directory$tag"
mkdir -p $cloudreg_drop

# Create a specific output
sample_oh_output=${sample_oh/stitched/cloudreg}
mkdir -p $sample_oh_output
echo $sample_oh_output

# Execute singularity container using estrin_precompute.sh script
singularity exec -B $sample_oh:/data/input -B $sample_oh_output:/data/output ~/cloudreg.sif bash ~/lightsheet_cluster/estrin_precompute.sh

echo If code worked, you may now cd into  ~/neuroglancer and run neuroglancer to look at brain on the scu-vis1 node. 

