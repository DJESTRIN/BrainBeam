#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#takes png and converts to tiff via Pillow

import argparse
from pathlib import Path
from tqdm import tqdm as tq
from PIL import Image

def pngtotiff(input_dir, output_dir=None):
    input_path = Path(input_dir).expanduser().resolve()
    output_path = Path(output_dir).expanduser().resolve() if output_dir else input_path

    files = sorted(input_path.rglob("*.png"))

    for file in tq(files):
        relative_file = file.relative_to(input_path).with_suffix(".tiff")
        destination = output_path / relative_file

        destination.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(file) as img:
            img.save(destination, "TIFF")
        
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="convert a .png file to a .TIFF file")
    parser.add_argument("--input_directory", type=str, help="the directory containing the input .png files", required=True)
    parser.add_argument("--output_directory", type=str, help="The directory containing the output .tiff files",required=False)
    args = parser.parse_args()
    pngtotiff(args.input_directory, args.output_directory)
