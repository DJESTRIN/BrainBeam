#!/bin/bash
stitch_dir=$1

cd $stitch_dir
folders=$( find $PWD -type d -name '*Ex*' )

for subf in $folders;
do 

cd $subf

find $PWD -name "*.tif*" -exec mv "{}" . \;

done
