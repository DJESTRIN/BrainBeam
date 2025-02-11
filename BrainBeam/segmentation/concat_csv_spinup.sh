#!/bin/bash
#SBATCH --job-name=concat_csvs         # Job name
#SBATCH --output=~/sbatch_logs/job_output_%j.log  # Standard output and error log
#SBATCH --ntasks=1                      # Number of tasks (usually 1 for batch jobs)
#SBATCH --time=02:00:00                 # Time limit (hh:mm:ss)
#SBATCH --mem=5G                        # Memory per node
#SBATCH --mail-type=BEGIN,END,FAIL      # Notifications
#SBATCH --mail-user=dje4001@med.cornell.edu  # Email address

# Parse command line inputs
codedir=$1 # Directory to segmentation sub folder
ilastikdir=$2  # Ilastik directory

# Ensure input arguments are provided
if [[ -z "$codedir" || -z "$ilastikdir" ]]; then
    echo "Usage: sbatch concat_csvs.sh <codedir> <ilastikdir>"
    exit 1
fi

# Ensure the code directory exists
if [[ ! -d "$codedir" ]]; then
    echo "Error: Code directory '$codedir' does not exist."
    exit 1
fi

# Search for all channel subfolders
find "$ilastikdir" -maxdepth 2 -type d -name '*Ex*' | while IFS= read -r subfolder; do
    echo "Submitting job for: $subfolder"

    sbatch --job-name=batch_ilastik \
        --mem=50G \
        --ntasks=4 \
        --cpus-per-task=8 \
        --partition=scu-cpu \
        --mail-type=BEGIN,END,FAIL \
        --mail-user=dje4001@med.cornell.edu \
        --wrap="source ~/.bashrc && \
        conda activate ~/anaconda3/envs/regular && \
        python \"$codedir/concat_csv.py\" --input_dir \"$subfolder\""
done