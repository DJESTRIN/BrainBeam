#!/bin/bash
echo on
input_folder=/athena/listonlab/store/dje4001/rsync_data/lightsheet/20220729_18_49_33_3811494_A#1018_P__Rabies__MPFC_CORT_CONTROL/
scratch_input_folder=/athena/listonlab/scratch/dje4001/20220729_18_49_33_3811494_A#1018_P__Rabies__MPFC_CORT_CONTROL/
scratch_output_folder=/athena/listonlab/scratch/dje4001/20220729_18_49_33_3811494_A#1018_P__Rabies__MPFC_CORT_CONTROL_drop/
mkdir -p  $scratch_output_folder

rsync -a --info=progress2 $input_folder $scratch_input_folder
pystripe -i $scratch_input_folder -o $scratch_output_folder -s1 256 -s2 64

echo off
