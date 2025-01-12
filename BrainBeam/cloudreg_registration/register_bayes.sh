#!/bin/bash
#SBATCH --job-name=bayesregister             # Job name
#SBATCH --output=./job_output_%j.log            # Standard output and error log
#SBATCH --ntasks=4                           # Number of tasks (usually 1 for batch jobs)
#SBATCH --cpus-per-task=4                    # Number of cpus per task
#SBATCH --time=08:00:00                      # Time limit (hh:mm:ss)
#SBATCH --mem=300G                           # Memory per node
#SBATCH --mail-type=BEGIN,END,FAIL           # Notifications
#SBATCH --mail-user=dje4001@med.cornell.edu  # Email address

#Parse command line inputs
input_path=$1
input_path=${input_path%[/\\]}
output_path=$2

# Set up paths for saving data
drop_path=$output_path/tiffsequence/
channel=$(basename $input_path)
exp=$(basename $(dirname $input_path))
mkdir -p $drop_path
mkdir -p /athena/listonlab/scratch/dje4001/cloudreg_base/${exp}_${channel}_autofluordata/

# Set up environment
source ~/.bashrc
module load matlab
conda activate cloudreg
cd ~/CloudReg

#Perform Bayesian optimized cloudreg registration
python3 -m cloudreg.scripts.bayes_registration --input_s3_path file://$input_path \
    --output_s3_path $output_path \
    --atlas_s3_path https://open-neurodata.s3.amazonaws.com/ara_2016/sagittal_50um/average_50um \
    --parcellation_s3_path https://open-neurodata.s3.amazonaws.com/ara_2016/sagittal_10um/annotation_10um_2017 \
    --atlas_orientation ASR \
    --orientation LPS \
    --rotation 0 0 0 \
    --translation 0 0 0 \
    --fixed_scale 1.3 \
    --missing_data_correction True \
    --grid_correction False \
    --bias_correction True \
    --regularization 5000.0 \
    --iterations 3000 \
    --registration_resolution 100

# Convert the registered atlas image to a tiff sequence
cloudreg_drop=/athena/listonlab/scratch/dje4001/cloudreg_base/${exp}_${channel}_registration/
rsync -av --remove-source-files --info=progress2 $cloudreg_drop $output_path

