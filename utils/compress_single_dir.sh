#!/bin/bash
#SBATCH --job-name=compress_single_dir
#SBATCH --output=/home/fs01/dje4001/sbatch_logs/compress_single_dir_%j.log
#SBATCH --error=/home/fs01/dje4001/sbatch_errors/compress_single_dir_%j.err
#SBATCH --time=02:00:00
#SBATCH --partition=scu-cpu
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --mem=100G

# Get the directory to compress from environment variable
DIR="$DIR"

# Check if the directory is provided
if [ -z "$DIR" ]; then
    echo "Error: No directory specified."
    exit 1
fi

# Compress the directory
echo "Compressing directory: $DIR"
tar -czf "${DIR}.tar.gz" -C "$(dirname "$DIR")" "$(basename "$DIR")"

# Check if the compression was successful
if [ $? -eq 0 ]; then
    echo "Compression successful: ${DIR}.tar.gz"
    
    # Remove the original directory
    rm -rf "$DIR"
    
    if [ $? -eq 0 ]; then
        echo "Original directory deleted: $DIR"
    else
        echo "Failed to delete original directory: $DIR"
    fi
else
    echo "Compression failed: $DIR"
fi

