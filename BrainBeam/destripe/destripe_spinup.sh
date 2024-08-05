#!/bin/bash/
#Passed variables from previous script
code_directory=$1
scratch_directory=$2
store_finish_directory=$3

#Update sample list (in the case of any issues)
scratch_raw=${scratch_directory}"lightsheet/converted/"
scratch_destriped=${scratch_directory}"lightsheet/destriped/"

# Create folder for destripe output
mkdir -p $scratch_destriped

#Loop through samples
for folder in $scratch_raw*/
do
    TMP=$(echo $folder)
    echo $TMP
    sbatch --job-name=destripe_files --mem=300G --partition=scu-cpu --mail-type=BEGIN,END,FAIL --mail-user=dje4001@med.cornell.edu --wrap="bash $code_directory/destripe.sh '$TMP' '$scratch_directory'"
done

sbatch --mem=50G --partition=scu-cpu --dependency=singleton --job-name=destripe_files --wrap="bash stitch_spinup.sh '$code_directory' '$scratch_directory' '$store_finish_directory'"


