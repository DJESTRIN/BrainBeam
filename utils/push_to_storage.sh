#!/bin/bash
source=$1
project=$2
destination=$3

drop=$destination/$project

rsync -var $source $drop
