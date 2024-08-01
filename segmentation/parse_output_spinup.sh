
#!/bin/bash
code_dir=$1
ilastik_input_dir=$2

cd $code_dir

# Get all slice folders in dir
slicesdirs=$( find $ilastik_input_dir -maxdepth 3 -type d -name '*slice*' )

for slicefolder in $slicesdirs;
do
echo $slicefolder
sbatch --job-name=parse_ilastik --mem=50G --cpus-per-task=8 --partition=scu-cpu --mail-type=BEGIN,END,FAIL --mail-user=dje4001@med.cornell.edu --wrap="bash ./parse_ilastik_output.sh '$slicefolder'"
done

#sbatch --mem=5G --partition=scu-cpu --dependency=singleton --job-name=parse_ilastik --wrap="bash ./combile_ilastik.sh $code_dir $ilastik_input_dir"

