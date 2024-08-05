#!/bin/bash

# Check if the correct number of arguments are provided
if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <directory>"
  exit 1
fi

DIRECTORY=$1

# Check if the provided argument is a directory
if [ ! -d "$DIRECTORY" ]; then
  echo "Error: $DIRECTORY is not a directory"
  exit 1
fi

# Loop through all directories in the provided directory
for dir in "$DIRECTORY"/*/; do
  # Skip if it's not a directory
  [ -d "$dir" ] || continue
  
  # Remove trailing slash
  dir=${dir%/}

  echo $dir
  
  # Get the directory name
  dir_name=$(basename "$dir")
  
  # Create a compressed tar.gz file
  tar -czf "$DIRECTORY/$dir_name.tar.gz" -C "$DIRECTORY" "$dir_name"
  
  # Remove the original directory after successful compression
  if [ $? -eq 0 ]; then
    rm -rf "$dir"
  else
    echo "Error compressing $dir_name"
  fi
done

echo "Compression completed."

