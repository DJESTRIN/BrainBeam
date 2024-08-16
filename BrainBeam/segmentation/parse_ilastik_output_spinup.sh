
#!/bin/bash

# parse command line inputs
code_dir=$1
ilastik_input_dir=$2

# Go to the code directory
cd $code_dir

# Get all slice folders in dir
slicesdirs=$( find $ilastik_input_dir -maxdepth 3 -type d -name '*slice*' )

# Loop over slice folders and parse ilastik's output
for slicefolder in $slicesdirs; do
    echo $slicefolder
    sbatch --job-name=parse_ilastik \
        --mem=50G \
        --cpus-per-task=8 \
        --partition=scu-cpu \
        --mail-type=BEGIN,END,FAIL \
        --mail-user=dje4001@med.cornell.edu \
        --wrap="bash ./parse_ilastik_output.sh '$code_dir' '$slicefolder'"
done

exit

