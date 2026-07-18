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

# Each sample is chained through remove_empty -> convert -> destripe -> stitch
# using --dependency=afterok on that SAME sample's previous job only. This means
# a fast sample can flow all the way through to stitching while a slower sample
# is still converting, instead of every sample being forced to wait at a
# step-wide barrier for the slowest sample in the batch to finish that step.
for folder in "$scratch_raw"*/; do
        TMP=$(echo "$folder")
        base_name=$(basename "$TMP")
        sample_converted="${scratch_converted}${base_name}/"
        echo "$TMP"

        remove_job_id=$(sbatch --parsable --job-name=remove_empty_images --mem=300G --partition=scu-cpu --mail-type=BEGIN,END,FAIL --mail-user=dje4001@med.cornell.edu --wrap="source ~/.bashrc && conda activate /home/fs01/dje4001/anaconda3/envs/regular && python '$script_directory/../utils/replaceempty.py' --pathway '$TMP'")

        convert_job_id=$(sbatch --parsable --dependency=afterok:"$remove_job_id" --job-name=convert_png_to_tiff --mem=300G --partition=scu-cpu --mail-type=BEGIN,END,FAIL --mail-user=dje4001@med.cornell.edu --wrap="source ~/.bashrc && conda activate /home/fs01/dje4001/anaconda3/envs/regular && python '$script_directory/convert_to_tiff.py' --input_directory '$TMP' --output_directory '$sample_converted'")

        destripe_job_id=$(sbatch --parsable --dependency=afterok:"$convert_job_id" --job-name=destripe_files --mem=300G --partition=scu-cpu --mail-type=BEGIN,END,FAIL --mail-user=dje4001@med.cornell.edu --wrap="bash '$script_directory/destripe.sh' '$sample_converted' '$scratch_directory'")

        sbatch --dependency=afterok:"$destripe_job_id" \
               --job-name=stitch_files \
               --mem=200G \
               --partition=scu-gpu \
               --gres=gpu:2 \
               --ntasks=4 \
               --cpus-per-task=4 \
               --mail-type=BEGIN,END,FAIL \
               --mail-user=dje4001@med.cornell.edu \
               --wrap="bash '$script_directory/../stitch/stitch.sh' '$TMP' '$scratch_directory'"
done



