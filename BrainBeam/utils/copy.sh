#!/bin/bash
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <search_path> <destination_root>"
    exit 1
fi

SEARCHPATH=$1
DESTINATION_ROOT=$2
base_name=$(basename "$SEARCHPATH")

mkdir -p "$DESTINATION_ROOT/lightsheet/raw/"
rsync -av --exclude '*MIP*' --info=progress2 -- "$SEARCHPATH" "$DESTINATION_ROOT/lightsheet/raw/$base_name/" #Copy folders but exclude max intensity projections.
