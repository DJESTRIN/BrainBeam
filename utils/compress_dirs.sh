#!/bin/bash
#SBATCH --job-name=submit_compression_jobs
#SBATCH --output=submit_compression_jobs_%j.log
#SBATCH --error=submit_compression_jobs_%j.err
#SBATCH --time=01:00:00
#SBATCH --partition=scu-cpu
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G

# Input directory
INPUT_DIR="$1"

# Check if the input directory is provided
if [ -z "$INPUT_DIR" ]; then
    echo "Usage: sbatch submit_compression_jobs.sh /path/to/input_directory"
    exit 1
fi

# Find directories that contain files and submit a job for each
find "$INPUT_DIR" -type d | while read -r dir; do
    # Check if the directory contains any files
    if find "$dir" -maxdepth 1 -type f | read; then
        # Submit a job for each directory
        sbatch --export=DIR="$dir" compress_single_dir.sh
    fi
done

