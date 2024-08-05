#!/bin/bash
#SBATCH --job-name=submit_compression_jobs
#SBATCH --output=/home/fs01/dje4001/sbatch_logs/submit_compression_jobs_%j.log
#SBATCH --error=/home/fs01/dje4001/sbatch_errors/submit_compression_jobs_%j.err
#SBATCH --time=01:00:00
#SBATCH --partition=scu-cpu
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G

# Input directory
INPUT_DIR="$1"

#Check if the input directory is provided
if [ -z "$INPUT_DIR" ]; then
    echo "Usage: sbatch submit_compression_jobs.sh /path/to/input_directory"
    exit 1
fi

# Find directories that contain files and submit a job for each
find "$INPUT_DIR" -type d | while read -r dir; do
    # Check if the directory contains any files
    if find "$dir" -maxdepth 1 -type f | read; then
        # Check if all files are .tar.gz
        all_tar_gz=true
        for file in "$dir"/*; do
            if [ -f "$file" ] && [[ ! "$file" =~ \.tar\.gz$ ]]; then
                all_tar_gz=false
                break
            fi
        done
        
        # Submit a job if not all files are .tar.gz
        if ! $all_tar_gz; then
            sbatch --export=DIR="$dir" $PWD/compress_single_dir.sh
        fi
    fi
done


