#!/bin/bash
#SBATCH --job-name=my_mpi_job           # Job name
#SBATCH --output=output_%j.txt          # Standard output and error log
#SBATCH --error=error_%j.txt            # Error log
#SBATCH --ntasks=4                      # Number of MPI tasks
#SBATCH --cpus-per-task=4               # Number of CPUs per task
#SBATCH --gres=gpu:2                    # Number of GPUs (2 GPUs)
#SBATCH --partition=gpu                 # Partition name (change as needed)
#SBATCH --time=24:00:00                 # Time limit (change as needed)

# Load necessary modules
module load cuda
export USECUDA_X_NCC=1
#module load openmpi/5.0.1
module load python/3.8                  # Adjust Python module if necessary
module load mpi4py                      # Load MPI module if needed

# Run the MPI program with Python
srun --mpi=pmi2 python /home/fs01/dje4001/Downloads/TeraStitcher-portable-1.11.10-Linux/parastitcher.py \
    -2 \
    --projin="/athena/listonlab/scratch/dje4001/lightsheet_scratch/rabies_cort_control_cohort2/lightsheet/destriped/20231109_18_47_15_CAGE4467198_ANIMAL3_VIRUSRABIES_SEXFEMALE_CORTCONTROL/Ex_561_Em_600/xml_import.xml" \
    --projout="/athena/listonlab/scratch/dje4001/lightsheet_scratch/rabies_cort_control_cohort2/lightsheet/destriped/20231109_18_47_15_CAGE4467198_ANIMAL3_VIRUSRABIES_SEXFEMALE_CORTCONTROL/Ex_561_Em_600/xml_displcomp" \
    --subvoldim=600 \
    --sV=25 \
    --sH=25 \
    --sD=0


