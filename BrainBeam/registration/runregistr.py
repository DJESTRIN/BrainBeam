#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: RunRegistration.py
Description: Primary script for running the alignment code
Author: David Estrin
Date: 2024-12-11
Version: 1.0
"""
# Import dependencies
import numpy as np
import os
import glob
from BrainBeam.registration.registrationimages import TargetImage, MovingImage, CellImage
from BrainBeam.registration.padding import zero_pad_arrays
from BrainBeam.registration.graphics import volume_graphics, slice_views, overlay_masks
from BrainBeam.registration.registration import alignment
from datetime import datetime
import argparse
import logging
import warnings
warnings.simplefilter("ignore")

def cli_parser():
    """ Takes command line inputs and parses them for downstream """
    # Create parser, add arguments and parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--image_path',type=str,help='Full path to best qualtiy light sheet images for registration ...')
    parser.add_argument('--atlas_path',type=str,help="Full path to folder containing atlas. If folder is empty, atlas is downloaded")
    parser.add_argument('--output_path',type=str,help='Full path containin results. Path will be appended with subfolder containing current date and time. \
                        These subfolders are where data will be saved.')
    parser.add_argument('--full_output_path', action='store_true', help = 'a full path to output_path')
    parser.add_argument('--align_binary_mask', default=None, action='store_true')
    parser.add_argument('--crop_border_noise_bool', default=None, action='store_true')
    parser.add_argument("--force_orientation", nargs='*', type=int, default=None,
                        help="Optional: 3 integers defining forced orientation (or omitted)")
    parser.add_argument("--force_flips", nargs='*', type=int, default=None,
                        help="Optional: 3 integers defining forced flips (or omitted)")
    args = parser.parse_args()

    # Parse through force orientation and flips
    if args.force_orientation == []:
        args.force_orientation = None
    if args.force_flips == []:
        args.force_flips = None
    if args.force_orientation is not None and len(args.force_orientation) != 3:
        parser.error("--force_orientation must have exactly 3 values or be omitted.")
    if args.force_flips is not None and len(args.force_flips) != 3:
        parser.error("--force_flips must have exactly 3 values or be omitted.")

    # Get current time as string and generate output folder
    now = datetime.now()
    init_date_time= now.strftime("%Y_%m_%d_%H_%M_%S")
    if args.full_output_path:
        output_path = args.output_path

    else:
        new_folder = f'current_run_{init_date_time}'
        output_path = os.path.join(args.output_path,new_folder)
        if not os.path.exists(output_path): 
            os.makedirs(output_path)

    # Append a few new arguments
    args.output_path = output_path
    args.init_date_time = init_date_time
    return args

def main(args, logger):
    # Push argument data to logger
    logger.info(f"This is the current image path: {args.image_path}")
    logger.info(f"This is the current output path: {args.output_path}")
    logger.info(f"Force flips is set to {args.force_flips}")
    logger.info(f"Force orientation is set to {args.force_orientation}")
    logger.info(f"Align binary mask is set to {args.align_binary_mask}")
    logger.info(f"Crop border noise is set to {args.crop_border_noise_bool}")

    # Update classes to have matching methods
    MovingImage.generate_gif = TargetImage.generate_gif 
    alignment.generate_gif = TargetImage.generate_gif 

    # Generate target image object
    target_oh = TargetImage(target_path=args.atlas_path, logger=logger)
    target_oh()
    target_oh.generate_gif(volume=target_oh.template,full_filename=os.path.join(args.output_path,f'init_target_array_{args.init_date_time}.gif'))  
   
    # Generate moving image object
    Image_oh = MovingImage(image_path = args.image_path, drop_path=args.output_path, logger=logger, 
                           force_orientations=args.force_orientation, force_flips=args.force_flips, crop_border_noise_bool = args.crop_border_noise_bool)
    Image_oh()
    Image_oh.generate_gif(volume=Image_oh.downsampled_volume,full_filename=os.path.join(args.output_path,f'init_moving_array_{args.init_date_time}.gif'))

    # Generate Cell Image object per csv file channel
    cell_count_files = glob.glob(os.path.join(args.output_path,'*cell_counts*csv'))
    if not cell_count_files:
        logger.warning("No cell files found.")

    cell_count_objs = []
    for cell_count_filename in cell_count_files:
        Cell_oh = CellImage(MovingImageObject=Image_oh, CellFile=cell_count_filename, logger=logger)
        Cell_oh()
        cell_count_objs.append(Cell_oh)
        Image_oh.generate_gif(volume=Cell_oh.downsampled_volume,full_filename=os.path.join(args.output_path,f'CHANNEL_{Cell_oh.channel_name}init_moving_array_{args.init_date_time}.gif'))

    # Perform alignment registration code
    graphobj = volume_graphics()
    alignment_object = alignment(MovingImageObject=Image_oh, TargetImageObject=target_oh, logger=logger, graphobjoh = graphobj, drop_path=args.output_path, align_binary_mask=args.align_binary_mask)
    alignment_object() 

    # Perform alignment on cell count objects
    logger.info(f"Aligning all cell count objects")
    cell_alignment_objs = []
    for Cell_oh in cell_count_objs:
        graphobj_cell = volume_graphics()
        alignment_object_cell = alignment(MovingImageObject=Cell_oh, TargetImageObject=target_oh, logger=logger, 
                                          graphobjoh = graphobj, drop_path=args.output_path, align_binary_mask=args.align_binary_mask)
        alignment_object_cell() 
        cell_alignment_objs.append(alignment_object_cell)


    # Generate 4D final array
    logger.info(f"Generating Mapped array and channel names array")
    zp_id_atlas_oh, _ = zero_pad_arrays(array1 = target_oh.annotation, array2 = alignment_object.target_array)
    mapped_array = np.stack([zp_id_atlas_oh,
                             alignment_object.target_array, 
                             alignment_object.nonrigid_moving_image], 
                             axis=3)
    
    # Gather count data for all channels and add to mapped array
    for alignment_object_cell in cell_alignment_objs:
        volumeoh = np.array(alignment_object_cell.nonrigid_moving_image)
        mapped_array =  np.concatenate((mapped_array, volumeoh[...,np.newaxis]), axis=3)

    # Gather channel names for seperate array
    all_channel_names = []
    for Cell_oh in cell_count_objs:
        all_channel_names.append(Cell_oh.channel_name)

    # Save data into numpy file 
    np.save(os.path.join(args.output_path,'mapped_array.npy'), mapped_array) 
    np.save(os.path.join(args.output_path,'channel_names.npy'), all_channel_names) 
    
    logger.info(f"Saved mapped_array and channel_names arrays")
   
if __name__=='__main__':
    # Get cli inputs
    args = cli_parser()

    # Set up logging for all events in code
    logging_file = os.path.join(args.output_path,'current_run_notes.log')
    if os.path.isfile(logging_file):
        os.remove(logging_file)

    logging.basicConfig(filename=logging_file, level=logging.INFO, 
                        format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("registration_logger")
    
    # Run main function using cli inputs
    main(args, logger)

    
    # Example local call
    
    # & C:/Users/listo/AppData/Local/anaconda3/envs/registration/python.exe c:/Users/listo/BrainBeam/BrainBeam/registration/RunRegistration.py --image_path C:\Users\listo\example_registration_data\sub2 --atlas_path C:\Users\listo\example_registration_data\test_registration_communal_drop\cage1582_animal22_registraton\atlas_drop --output_path C:\Users\listo\example_registration_data\c200a4 --full_output_path
    
    