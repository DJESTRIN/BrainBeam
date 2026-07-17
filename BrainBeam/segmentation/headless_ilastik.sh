#!/bin/bash
project_file=$1
inputdir=$2
cd "$inputdir"

while IFS= read -r -d '' sd; do
	npfile=$(find "$sd" -type f \( -name '*.npy' -o -name '*.npz' \) -print -quit)

	if [ -z "${npfile}" ]; then
		mapfile -d '' stack_files < <(find "$sd" -maxdepth 1 -type f -name 'image*.tiff' -print0 | sort -z)
		if [ "${#stack_files[@]}" -eq 0 ]; then
			echo "No TIFF stack found in $sd"
			continue
		fi
		echo "Processing ${#stack_files[@]} TIFF files from $sd"
		cd ~/Downloads/ilastik-1.4.0-Linux/

		./run_ilastik.sh --headless --project="$project_file" --output_format=numpy --stack_along="z" "${stack_files[@]}"
	else
		echo "This path had a numpy file"
		echo "$sd"
	fi
done < <(find "$PWD" -type d -name '*_*' -print0)

exit
