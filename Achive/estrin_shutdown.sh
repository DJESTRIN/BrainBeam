#!/bin/bash/
#Passed variables from previous script
code_directory=$1
scratch_directory=$2
store_finish_directory=$3

# Push everything back to storage
rsync -av $scratch_directorylightsheet/destriped/ $store_directory/destriped/
rsync -av $scratch_directorylightsheet/stitched/ $store_directory/stiched/

exit
