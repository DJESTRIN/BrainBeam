#!/bin/bash
#SBATCH --job-name=submit_compression_jobs
#SBATCH --output=/home/fs01/dje4001/sbatch_logs/submit_decompression_jobs_%j.log
#SBATCH --error=/home/fs01/dje4001/sbatch_errors/submit_decompression_jobs_%j.err
#SBATCH --time=01:00:00
#SBATCH --partition=scu-cpu
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G

# Input directory
INPUT_DIR="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

#Check if the input directory is provided
if [ -z "$INPUT_DIR" ]; then
    echo "Usage: sbatch submit_compression_jobs.sh /path/to/input_directory"
    exit 1
fi

# Find .tar.gz files and submit them for decompression
find "$INPUT_DIR" -type d | while read -r dir; do
    find "$dir" -maxdepth 1 -type f -name "*.tar.gz" -print0 | while IFS= read -r -d '' tar_file; do
        sbatch --export=TAR_FILE="$tar_file" "$SCRIPT_DIR/decompress_single_dir.sh"
    done
done


