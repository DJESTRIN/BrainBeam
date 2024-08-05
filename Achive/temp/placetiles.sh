#!/bin/bash
xmlpath=$1
outputpath=$2

echo $xmlpath
echo $outputpath

source ~/.bashrc
module load cuda
module load openmpi/5.0.1
module load ucx/1.11.2  libfabric/1.13.0
export USECUDA_X_NCC=1
conda activate /home/fs01/dje4001/anaconda3/envs/stitch

cd /home/fs01/dje4001/Downloads/TeraStitcher-portable-1.11.10-Linux/

# Merge files using CPU not gpu
./terastitcher --merge --projin="$xmlpath" --volout="$outputpath" --volout_plugin="TiledXY|2Dseries" --slicewidth=100000 --sliceheight=150000

