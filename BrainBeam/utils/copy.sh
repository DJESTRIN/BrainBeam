#!/bin/bash
SEARCHPATH=$1
base_name=${basename $SEARCHPATH}

mkdir -p $2/lightsheet/raw/
rsync -av --exclude '*MIP*' --info=progress2 ${SEARCHPATH} $2/lightsheet/raw/$base_name/ #Copy folders but exclude max intensity projections.
