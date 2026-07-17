#!/bin/bash
set -e
shopt -s nullglob

#Passed variables from previous script
script_directory="$(cd "$(dirname "$0")" && pwd)"
code_directory=$1
scratch_directory=$2
store_finish_directory=$3

#Update sample list (in the case of any issues)
scratch_root="${scratch_directory%/}"
scratch_raw="${scratch_root}/lightsheet/raw/"
scratch_converted="${scratch_root}/lightsheet/converted/"
mkdir -p "$scratch_converted"

# Python script replacing 0 byte files with empty images.
for folder in "$scratch_raw"*/; do
        TMP=$(echo "$folder")
        echo "$TMP"
        remove_job_id=$(sbatch --parsable --job-name=remove_empty_images --mem=300G --partition=scu-cpu --mail-type=BEGIN,END,FAIL --mail-user=dje4001@med.cornell.edu --wrap="source ~/.bashrc && conda activate /home/fs01/dje4001/anaconda3/envs/regular && python '$script_directory/../utils/replaceempty.py' --pathway '$TMP'")
        sbatch --dependency=afterok:"$remove_job_id" --job-name=convert_png_to_tiff --mem=300G --partition=scu-cpu --mail-type=BEGIN,END,FAIL --mail-user=dje4001@med.cornell.edu --wrap="source ~/.bashrc && conda activate /home/fs01/dje4001/anaconda3/envs/regular && python '$script_directory/convert_to_tiff.py' --input_directory '$TMP' --output_directory '$scratch_converted'"
done

sbatch --mem=50G --partition=scu-cpu --dependency=singleton --job-name=convert_png_to_tiff --wrap="bash '$script_directory/destripe_spinup.sh' '$code_directory' '$scratch_directory' '$store_finish_directory'"



