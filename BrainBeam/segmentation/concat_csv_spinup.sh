#!/bin/bash
#SBATCH --job-name=concat_csvs         # Job name
#SBATCH --output=~/sbatch_logs/job_output_%j.log            # Standard output and error log
#SBATCH --ntasks=1                            # Number of tasks (usually 1 for batch jobs)
#SBATCH --time=02:00:00                       # Time limit (hh:mm:ss)
#SBATCH --mem=5G                             # Memory per node
#SBATCH --mail-type=BEGIN,END,FAIL           # Notifications
#SBATCH --mail-user=dje4001@med.cornell.edu  # Email address

# Parse command line inputs
ilastikdir=$1 #ilastik directory

#Search for all channel subfolders
subfolders=$(find $ilastikdir -maxdepth 2 -type d -name '*Ex*')

# Loop over folders and begin concatonating ilastik csv files. 
for subfolder in $subfolders; do
    echo $subfolder
    sbatch --job-name=batch_ilastik \
        --mem=50G \
        --ntasks=4 \
        --cpus-per-task=8 \
        --partition=scu-cpu \
        --mail-type=BEGIN,END,FAIL \
        --mail-user=dje4001@med.cornell.edu \
        --wrap="python ./concat_csv.py  --input_dir '$subfolder'"
done 

