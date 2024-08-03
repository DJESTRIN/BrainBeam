#!/bin/bash
#SBATCH --job-name=decompress_single_file
#SBATCH --output=/home/fs01/dje4001/sbatch_logs/decompress_single_file_%j.log
#SBATCH --error=/home/fs01/dje4001/sbatch_errors/decompress_single_file_%j.err
#SBATCH --time=02:00:00
#SBATCH --partition=scu-cpu
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --mem=100G

# Get the tar.gz file to decompress from the environment variable
TAR_FILE="$TAR_FILE"

# Check if the tar.gz file is provided
if [ -z "$TAR_FILE" ]; then
    echo "Error: No tar.gz file specified."
    exit 1
fi

# Decompress the tar.gz file
echo "Decompressing file: $TAR_FILE"
tar -xzf "$TAR_FILE" -C "$(dirname "$TAR_FILE")"

# Check if the decompression was successful
if [ $? -eq 0 ]; then
    echo "Decompression successful: $TAR_FILE"
    
    # Remove the tar.gz file
    rm -f "$TAR_FILE"
    
    if [ $? -eq 0 ]; then
        echo "Original tar.gz file deleted: $TAR_FILE"
    else
        echo "Failed to delete original tar.gz file: $TAR_FILE"
    fi
else
    echo "Decompression failed: $TAR_FILE"
fi
