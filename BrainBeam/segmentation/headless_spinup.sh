#!/bin/bash
#SBATCH --job-name=stitching_pipeline         # Job name
#SBATCH --output=job_output_%j.log            # Standard output and error log
#SBATCH --ntasks=1                            # Number of tasks (usually 1 for batch jobs)
#SBATCH --time=02:00:00                       # Time limit (hh:mm:ss)
#SBATCH --mem=5G                             # Memory per node
#SBATCH --mail-type=BEGIN,END,FAIL           # Notifications
#SBATCH --mail-user=dje4001@med.cornell.edu  # Email address

# Parse command line inputs
code_dir=$1
ilastik_input_dir=$2
ilastik_file=$3

# Go to code directory
cd $code_dir

# Get all slice folders in dir
slicesdirs=$( find $ilastik_input_dir -type d -name '*slice*' )

# Loop over slice folders and pass to ilastik bash script
for slicefolder in $slicesdirs; do
    echo $slicefolder
    sbatch --job-name=batch_ilastik \
        --mem=50G \
        --ntasks=4 \
        --cpus-per-task=8 \
        --partition=scu-cpu \
        --mail-type=BEGIN,END,FAIL \
        --mail-user=dje4001@med.cornell.edu \
        --wrap="bash ./headless_ilastik.sh '$ilastik_file' '$slicefolder'"

done

exit 
