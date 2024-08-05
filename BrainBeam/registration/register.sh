#!/bin/bash
# This script is currently not automated 

# DO NOT ADD AN EXTRA '/' AFTER INPUT. Input should equal /animal/Ex_647_Em_680  ... NEVER /animal/Ex_647_Em_680/

# Remember to first edit the following variables:
# atlas oreintation
# orientation
# rotation
# translation
# fixed scale

# THEN run an interactive slurm session with GPU: 
#srun --job-name=registration --mem=200G --parition=scu-gpu,sackler-gpu --gres=gpu:2 --mail-type=BEGIN,END,FAIL --mail-user=dje4001@med.cornell.edu 
#screen
#bash ./estrin_register.sh input output
#sbatch --job-name=registration --mem=400G --partition=sackler-cpu,scu-cpu --mail-type=BEGIN,END,FAIL --mail-user=dje4001@med.cornell.edu --wrap="bash estrin_register.sh $input $output"


#Variables passed from previous script
input_path=$1
output_path=$2
drop_path=$output_path/tiffsequence/
channel=$(basename $input_path)
exp=$(basename $(dirname $input_path))

mkdir -p $drop_path
mkdir -p /athena/listonlab/scratch/dje4001/cloudreg_base/${exp}_${channel}_autofluordata/

source ~/.bashrc
module load matlab
conda activate cloudreg
cd ~/CloudReg

#Perform Cloudreg registration
python3 -m cloudreg.scripts.estrin_register -input_s3_path file://$input_path --output_s3_path $output_path --atlas_s3_path https://open-neurodata.s3.amazonaws.com/ara_2016/sagittal_50um/average_50um --parcellation_s3_path https://open-neurodata.s3.amazonaws.com/ara_2016/sagittal_10um/annotation_10um_2017 --atlas_orientation ASR -orientation LPS --rotation 32.8 -3.3 2.2 --translation 0 0 0 --fixed_scale 1.2 --missing_data_correction True --grid_correction False --bias_correction True --regularization 5000.0 --iterations 3000 --registration_resolution 100

# Convert the registered atlas image to a tiff sequence
cloudreg_drop=/athena/listonlab/scratch/dje4001/cloudreg_base/${exp}_${channel}_registration/
rsync -av --remove-source-files --info=progress2 $cloudreg_drop $output_path

transformation_image=$output_path/downloop_1_labels_to_target_highres.img
conda activate spyder-env

cd ~/lightsheet_cluster
#python convert_image.py --input_image_path $transformation_image --output_path $drop_path --target_image_sizex 7428 --target_image_sizey 8810 --mode nearest
