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
run_one=${3:-false} # Run a single sample folder then stop (useful for quick testing)

# Create folder for terastitcher output
scratch_root="${scratch_directory%/}/"
scratch_stitch="${scratch_root}lightsheet/stitched/"
scratch_destriped="${scratch_root}lightsheet/destriped/"
mkdir -p "$scratch_stitch"

# Update sample list (in the case of any issues)
cd "$code_directory" || exit 1
shopt -s nullglob
stitch_inputs=("${scratch_destriped}"*/)
stitch_job_ids=()

if [ ${#stitch_inputs[@]} -eq 0 ]; then
       echo "No destriped sample directories found in $scratch_destriped"
       exit 1
fi

# Submit jobs to process images using terastitcher
for i in "${stitch_inputs[@]}"; do
       TMP=$(echo "$i")
       submitted_job_id=$(sbatch --parsable \
              --job-name=stitch_files \
              --mem=200G \
              --partition=scu-gpu \
              --gres=gpu:2\
              --ntasks=4 \
              --cpus-per-task=4 \
              --mail-type=BEGIN,END,FAIL \
              --mail-user=dje4001@med.cornell.edu \
              --wrap="bash ./stitch.sh '$TMP' '$scratch_root'") || exit 1
       stitch_job_ids+=("$submitted_job_id")
       
       # Run a single folder and then break
       if [ "$run_one" = true ]; then
              break
       fi 
done

# Block this driver job until every per-sample stitch job reaches a terminal SLURM
# state, so this job's own completion reflects the real per-sample work finishing
# instead of exiting the instant all the per-sample jobs were merely *submitted*.
# This also lets the GUI (or another script) safely chain a --dependency=afterok on
# THIS job's id and know that means "stitching is actually done for every sample".
echo "Waiting on ${#stitch_job_ids[@]} per-sample stitch job(s) to finish: ${stitch_job_ids[*]}"
pending=("${stitch_job_ids[@]}")
failed=0
while [ ${#pending[@]} -gt 0 ]; do
       sleep 30
       still_pending=()
       for job_id in "${pending[@]}"; do
              state=$(sacct -j "$job_id" --format=State --noheader --parsable2 2>/dev/null | head -n1 | awk '{print $1}')
              case "$state" in
                     COMPLETED) ;;
                     FAILED|CANCELLED*|TIMEOUT|OUT_OF_MEMORY|NODE_FAIL) failed=1 ;;
                     *) still_pending+=("$job_id") ;;   # still running/pending, or not visible in sacct yet
              esac
       done
       pending=("${still_pending[@]}")
done

if [ "$failed" -eq 1 ]; then
       echo "One or more per-sample stitch jobs failed - see sacct/job logs for details."
       exit 1
fi
echo "All per-sample stitch jobs finished successfully."

