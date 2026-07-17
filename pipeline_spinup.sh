#!/bin/bash
set -euo pipefail

script_directory="$(cd "$(dirname "$0")" && pwd)"
code_directory="$script_directory"
copy_script="$code_directory/BrainBeam/utils/copy.sh"
convert_spinup_script="$code_directory/BrainBeam/destripe/convert_tiff_spinup.sh"

echo "This is your code directory: $code_directory"

if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <scratch_directory> <store_start_directory> <store_finish_directory>"
    exit 1
fi

scratch_directory=$1
store_start_directory=$2
store_finish_directory=$3

echo "This is your scratch directory: $scratch_directory"
echo "This is your start directory: $store_start_directory"
echo "This is your end directory: $store_finish_directory"

if [ ! -d "$store_start_directory" ]; then
    echo "Error: start directory does not exist: $store_start_directory"
    exit 1
fi

if [ ! -f "$copy_script" ]; then
    echo "Error: copy helper script not found: $copy_script"
    exit 1
fi

if [ ! -f "$convert_spinup_script" ]; then
    echo "Error: TIFF conversion spinup script not found: $convert_spinup_script"
    exit 1
fi

mkdir -p "$scratch_directory"
mkdir -p "$scratch_directory/lightsheet"
mkdir -p "$store_finish_directory"

copy_job_ids=()
while IFS= read -r -d '' sample_directory; do
    echo "$sample_directory"
    copy_job_id=$(sbatch --parsable \
        --job-name=copying_files \
        --mem=300G \
        --partition=scu-cpu \
        --mail-type=BEGIN,END,FAIL \
        --mail-user=dje4001@med.cornell.edu \
        --wrap="bash '$copy_script' '$sample_directory' '$scratch_directory'") || exit 1
    copy_job_ids+=("$copy_job_id")
done < <(find "$store_start_directory" -maxdepth 1 -mindepth 1 -type d -print0)

if [ ${#copy_job_ids[@]} -eq 0 ]; then
    echo "No sample directories found in $store_start_directory"
    exit 1
fi

copy_dependency="afterok:$(IFS=:; echo "${copy_job_ids[*]}")"
sbatch --parsable \
    --mem=50G \
    --partition=scu-cpu \
    --dependency="$copy_dependency" \
    --job-name=convert_png_to_tiff \
    --wrap="bash '$convert_spinup_script' '$code_directory' '$scratch_directory' '$store_finish_directory'"
