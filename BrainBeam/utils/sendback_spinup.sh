#!/bin/bash
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <input_dir> <output_root> <job_name>"
    exit 1
fi

input_dir=$1
output_foldername="$2/$3"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$input_dir" || exit 1

# Move all sample data to storage
find "$input_dir" -maxdepth 1 -mindepth 1 -type d -print0 | while IFS= read -r -d '' sample
do 
echo "$sample"
sample_name=$(basename "$sample")
sbatch --job-name=store_files --mem=100G --partition=scu-cpu,sackler-cpu --mail-type=BEGIN,END,FAIL --mail-user=dje4001@med.cornell.edu --wrap="bash '$script_dir/sendback.sh' '$sample' '$sample_name' '$output_foldername'"
done 
