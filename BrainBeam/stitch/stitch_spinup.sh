#!/bin/bash
#SBATCH --job-name=stitching_pipeline         # Job name
#SBATCH --output=job_output_%j.log            # Standard output and error log
#SBATCH --ntasks=1                            # Number of tasks (usually 1 for batch jobs)
#SBATCH --time=02:00:00                       # Time limit (hh:mm:ss)
#SBATCH --mem=5G                             # Memory per node
#SBATCH --mail-type=BEGIN,END,FAIL           # Notifications
#SBATCH --mail-user=dje4001@med.cornell.edu  # Email address

# Passed variables from previous script
code_directory=$1
scratch_directory=$2
run_dependencies=${3:-true} # recalculate all files
run_one=${4:-false} #

# Create folder for terastitcher output
scratch_stitch="${scratch_directory}lightsheet/stitched/"
scratch_destriped="${scratch_directory}lightsheet/destriped/"
mkdir -p "$scratch_stitch"

# Update sample list (in the case of any issues)
cd "$code_directory"

# Submit jobs to process images using terastitcher
for i in ${scratch_destriped}*/; do
       TMP=$(echo "$i")
       sbatch --job-name=stitch_files \
              --mem=50G \
              --partition=scu-cpu \
              --mail-type=BEGIN,END,FAIL \
              --mail-user=dje4001@med.cornell.edu \
              --wrap="bash ./stitch.sh '$TMP' '$scratch_directory'"
       
       # Run a single folder and then break
       if [ "$run_one" = true ]; then
              break
       fi 
done

if [ "$run_dependencies" = false ]; then 
       # Submit jobs for neuroglancer/cloudreg processing
       sbatch --mem=5G \
              --partition=scu-cpu \
              --dependency=singleton \
              --job-name=cloudreg_processing \
              --wrap="bash cloudreg_spinup.sh '$code_directory' '$scratch_directory'"

       # Submit jobs for generating cubes for validation analysis
       sbatch --mem=5G \
              --partition=scu-cpu \
              --dependency=singleton \
              --job-name=cube_generation \
              --wrap="bash traindata_spinup.sh '$code_directory' '$scratch_directory'"

       # Submit jobs for segmenting cells
       sbatch --mem=5G \
              --partition=scu-cpu \
              --dependency=singleton \
              --job-name=segmentation \
              --wrap="bash segmentation_spinup.sh '$code_directory' '$scratch_directory'"

       exit
fi
