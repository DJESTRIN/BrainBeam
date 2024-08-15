#!/bin/bash
#SBATCH --job-name=compress_single_dir
#SBATCH --output=/home/fs01/dje4001/sbatch_logs/compress_single_dir_%j.log
#SBATCH --error=/home/fs01/dje4001/sbatch_errors/compress_single_dir_%j.err
#SBATCH --time=04:00:00
#SBATCH --partition=scu-cpu
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --mem=100G

# Specify the directory containing the files to compress
DIRECTORY=$1

# Change to the specified directory
cd "$DIRECTORY" || exit

# Loop through each file in the directory
for FILE in *; do
    # Check if it is a regular file (not a directory or other type of file)
    if [ -f "$FILE" ]; then
        # Tar and gzip the file
        tar -czf "$FILE.tar.gz" "$FILE"
     
        if [ $? -eq 0 ]; then
            # Remove the original file
            rm "$FILE"
        else
            echo "Failed to create $FILE.tar.gz"
        fi

    fi
done