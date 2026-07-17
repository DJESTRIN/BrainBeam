#!/bin/bash
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <source> <project> <destination>"
    exit 1
fi

source_path=$1
project=$2
destination=$3

drop=$destination/$project

mkdir -p "$drop"
rsync -var -- "$source_path" "$drop"
