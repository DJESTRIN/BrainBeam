#!/bin/bash/
#Passed variables from previous script
code_directory=$1
scratch_directory=$2
store_finish_directory=$3

#Update sample list (in the case of any issues)
scratch_raw=${scratch_directory}"lightsheet/raw/"
scratch_converted=${scratch_directory}"lightsheet/converted/"
mkdir -p $scratch_converted

# Python script replacing 0 byte files with empty images.
for folder in $scratch_raw*/
do
        TMP=$(echo $folder)
        echo $TMP
        sbatch --job-name=remove_empty_images --mem=300G --partition=scu-cpu --mail-type=BEGIN,END,FAIL --mail-user=dje4001@med.cornell.edu --wrap="source ~/.bashrc && conda activate /home/fs01/dje4001/anaconda3/envs/regular && python '$code_directory'/replaceempty.py --pathway '$TMP'"

done

#Loop through samples
for folder in $scratch_raw*/
do
        TMP=$(echo $folder)
        echo $TMP
        sbatch --job-name=convert_png_to_tiff --mem=300G --partition=scu-cpu --mail-type=BEGIN,END,FAIL --mail-user=dje4001@med.cornell.edu --wrap="source ~/.bashrc && conda activate /home/fs01/dje4001/anaconda3/envs/regular && python $code_directory/convert_to_tiff.py --input_directory '$TMP' --output_directory '$scratch_converted'"
done

sbatch --mem=50G --partition=scu-cpu --dependency=singleton --job-name=convert_png_to_tiff --wrap="bash destripe_spinup.sh '$code_directory' '$scratch_directory' '$store_finish_directory'"




