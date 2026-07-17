#!/bin/bash
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <sample> <sample_name> <output_root>"
    exit 1
fi

sample=$1
sample_name=$2
output_path="$3/$sample_name"
echo "$output_path"
mkdir -p "$output_path"
rsync -av --remove-source-files --info=progress2 -- "$sample" "$output_path"
