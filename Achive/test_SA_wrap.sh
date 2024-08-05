#!/bin/bash
module load cuda
source ~/.bashrc
conda activate new_cell_counting

cd ~/LIGHTSHEET_CLUSTER/SA_files/
python ~/lightsheet_cluster/test_SA.py
