#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: multinoderegistration.py
Description: 
Author: David Estrin
Date: 2025-01-15
Version: 1.0
"""

# Load dependencies 
import os,glob
import subprocess
import argparse
import pickle
import shutil
import time
import ipdb
#from BrainBeam.registration.monitorprocess import monitor

# Build custom class for gather all path data and submitting jobs via slurm
class managepaths():
    def __init__(self, base_stitched_image_path, base_cell_count_path, base_registration_output_path = None):
        # Set up attributes
        self.base_stitched_image_path = base_stitched_image_path
        self.base_cell_count_path = base_cell_count_path

        # Make sure a real path was given
        assert os.path.exists(self.base_stitched_image_path)
        assert os.path.exists(self.base_cell_count_path)

        # Generate output folder if not created
        if base_registration_output_path is None:
            parent_folder = os.path.dirname(os.path.abspath(self.base_stitched_image_path))
            self.base_registration_output_path = os.path.join(parent_folder,"/registration")
        else:
            self.base_registration_output_path = base_registration_output_path

        if not os.path.exists(self.base_registration_output_path):
            os.mkdir(self.base_registration_output_path)

    def find_image_paths(self):
        """ Given a base image path, find all subfolders """
        self.image_folders = set()
        # Loop over all images found and add parent dirs to the set
        for file in glob.iglob(f"{self.base_stitched_image_path}/**/*.tif*", recursive=True):
            subfolder = os.path.dirname(file)

            if subfolder not in self.image_folders:
                self.image_folders.add(subfolder)
                print(f"New folder added: {subfolder}")

    def find_cell_count_files(self):
        """ Given a base cell count path, find all cell count files """
        self.cell_count_files = set()
        # Loop over all images found and add csv files to the set
        for file in glob.iglob(f"{self.base_cell_count_path}/**/*cell_count*.csv*", recursive=True):
            if file not in self.cell_count_files:
                self.cell_count_files.add(file)
                print(f"New file added: {file}")

    def extract_path_info(self, path_oh):
        # Get the subfolder
        parts = path_oh.strip('/').split('/')
        for part in parts:
            if "cage" in part.lower() and "animal" in part.lower():
                important_part = part
                break

        # Find the cage and subject information
        parts = important_part.strip('_').split('_')
        cage = None
        subject = None
        for part in parts:
            if "cage" in part.lower():
                cage = part.lower()
            if "animal" in part.lower():
                subject = part.lower()

        return cage, subject

    def align_files_to_folders(self):

        # Loop over all image folders and csv files to find matches
        # Place all matches in a dictrionary
        self.matching_paths_dictionary = {}
        for folders_oh in self.image_folders:
            folder_oh_cage, folder_oh_subject = self.extract_path_info(folders_oh)
            matches = []

            for file_oh in self.cell_count_files:
                file_oh_cage, file_oh_subject = self.extract_path_info(file_oh)
                
                if folder_oh_cage == file_oh_cage and folder_oh_subject == file_oh_subject:
                    matches.append(file_oh)

            if matches:
                self.matching_paths_dictionary[folders_oh] = matches

        # Convert set's to lists for future use
        self.image_folders = list(self.image_folders)
        self.cell_count_files = list(self.cell_count_files)

    def set_registration_outputs(self):
        """ Set up output folders for registration """
        self.atlas_drop_paths = []
        self.registration_drop_paths = []
        for folders_oh in self.image_folders:
            folder_oh_cage, folder_oh_subject = self.extract_path_info(folders_oh)
            ipdb.set_trace()
            output_folder_base = os.path.join(self.base_registration_output_path,f"/{folder_oh_cage}_{folder_oh_subject}_registration")

            # Make the base folder for current subject
            if not os.path.exists(output_folder_base):
                os.mkdir(output_folder_base)

            # Make atlas drop path
            output_folder_base_atlas = os.path.join(output_folder_base,"/atlas")
            if not os.path.exists(output_folder_base_atlas):
                os.mkdir(output_folder_base_atlas)
            self.atlas_drop_paths.append(output_folder_base_atlas)

            # Make registration drop path 
            output_folder_base_dropoh = os.path.join(output_folder_base,"/registration_drop")
            if not os.path.exists(output_folder_base_dropoh):
                os.mkdir(output_folder_base_dropoh)

        # Create common folder where figures are copied to for quick viewing
        self.communal_drop_folder = os.path.join(self.base_registration_output_path,"/communal_figures")
        if not os.path.exists(self.communal_drop_folder):
            os.mkdir(self.communal_drop_folder)

        # Save a list of output folders to be monitored by other code
        with open(os.path.join(self.communal_drop_folder,"/running_directories.pkl"),"wb") as f:
            pickle.dump(self.registration_drop_paths, f)
            print(f"Registration drop paths saved to pickle file in communal drop folder.")

    def determine_channel(self,path):
        channel = None
        if '488' in path:
            channel = 488
        if '561' in path:
            channel = 561
        if '647' in path:
            channel = 647
        if '785' in path:
            channel = 785
        return str(channel)

    def copy_cell_counts(self):
        """ Copy cell count files to corresponding registration drop paths. 
            Append channel information in the process.  """
        for drop_path in self.registration_drop_paths:
            for _, cell_count_files in self.matching_paths_dictionary.items():
                for file_oh in cell_count_files:
                    file_oh_cage, file_oh_subject = self.extract_path_info(file_oh)
                    drop_oh_cage, drop_oh_subject = self.extract_path_info(drop_path)

                    if file_oh_cage==drop_oh_cage and file_oh_subject==drop_oh_subject:
                        channel_oh = self.determine_channel(file_oh)
                        assert channel_oh is not None

                        # Copy file to output location
                        shutil.copy2(file_oh, os.path.join(drop_path,f"/{file_oh_cage}_{file_oh_subject}_channel{channel_oh}_cell_counts.csv"))
    
    def load_force_flips(self):
        for drop_path in self.registration_drop_paths:
            if os.path.exists(os.path.join(drop_path,"force_flips.txt")):
                with open(os.path.join(drop_path,"force_flips.txt"), 'r') as file:
                    self.force_flips = [int(line.strip()) for line in file]
            else:
                self.force_flips = None
    
    def load_force_orientations(self):
        for drop_path in self.registration_drop_paths:
            if os.path.exists(os.path.join(drop_path,"force_orientations.txt")):
                with open(os.path.join(drop_path,"force_orientations.txt"), 'r') as file:
                    self.force_orientations = [int(line.strip()) for line in file]
            else:
                self.force_orientations = None
    
    def load_align_binary_mask_file(self):
        for drop_path in self.registration_drop_paths:
            if os.path.exists(os.path.join(drop_path,"align_binary_mask.txt")):
                with open(os.path.join(drop_path,"align_binary_mask.txt"), 'r') as file:
                    self.align_binary_mask = [int(line.strip()) for line in file]
            else:
                self.align_binary_mask = None

    def set_slurm_output_folders(self):
        """ Create output folders where slurm log and error data will be stored for ease of use """
        self.communal_slurm_log_directory = os.path.join(self.base_registration_output_path,"/slurm_logs")
        if not os.path.exists(self.communal_slurm_log_directory):
            os.mkdir(self.communal_slurm_log_directory)

        self.communal_slurm_error_directory = os.path.join(self.base_registration_output_path,"/slurm_errors")
        if not os.path.exists(self.communal_slurm_error_directory):
            os.mkdir(self.communal_slurm_error_directory)
        
    def __call__(self):
        # General pipeline for class
        print('Finding image paths')
        self.find_image_paths()

        print('Finding cell count paths')
        self.find_cell_count_files()

        print('Aligning paths')
        self.align_files_to_folders()

        print('Setting outputs')
        self.set_registration_outputs()

        print('Copying files')
        self.copy_cell_counts()

        print('Loading manual settings')
        self.load_force_flips()
        self.load_force_orientations()
        self.load_align_binary_mask_file()

        print('Set slurm output')
        self.set_slurm_output_folders()

def submit_jobs(managepathobj, conda_environment_name, partition_oh = 'scu-cpu', email = 'dje4001@med.cornell.edu', 
                memory_per_job = 128, tasks_per_job = 8, cpus_per_task = 4):
    """ Build sbatch command and submit for running """
    jids = []
    for subject_oh_data in managepathobj.matching_paths_dictionary.items():
        ipdb.set_trace()
        image_path_oh, count_files_oh, output_atlas_path_oh, output_registration_path_oh, binary_mask_file, force_orientation_file, force_flips_file = subject_oh_data
        my_command = f"sbatch --job-name=merge_data_to_tallformat \
                --mem={memory_per_job}G \
                --ntasks={tasks_per_job} \
                --cpus-per-task={cpus_per_task} \
                --partition={partition_oh} \
                --mail-type=BEGIN,END,FAIL \
                --mail-user={email} \
                --output={managepathobj.communal_slurm_log_directory}/%x-%j.out \
                --error={managepathobj.communal_slurm_error_directory}/%x-%j.err \
                --wrap='source ~/.bashrc && conda activate {conda_environment_name} && python ./registration.py \
                --image_path {image_path_oh} \
                --atlas_path {output_atlas_path_oh} \
                --output_path {output_registration_path_oh} \
                --full_output_path \
                --align_binary_mask {binary_mask_file} \
                --force_orientation {force_orientation_file} \
                --force_flips {force_flips_file}'"

        result = subprocess.run([my_command], shell=True, capture_output=True, text=True)
        idoh = result.stdout.strip()
        print(f'Submitted job number: {idoh}')
        jids.append(idoh)
    return jids

def cli_parser():
    parser = argparse.ArgumentParser(description="Get all main directories")
    parser.add_argument('--parent_image_path', type=str, required=True, help='Image path containing all subject to be run')
    parser.add_argument('--parent_segmentation_path', type=str, required=True, help='Segmentation path containing all subjects cell count files to be run')
    parser.add_argument('--parent_registration_output_path', type=str, default=None, help='Parent output folder')
    parser.add_argument('--conda_environment_name', type=str, required=True, help='Conda environment needed for registration')
    parser.add_argument('--partition', type=str, default='scu-cpu', help='slurm partition to use')
    parser.add_argument('--user_email', type=str, default='dje4001@med.cornell.edu', help='Email to use for slurm' )
    parser.add_argument('--memory', type=str, default='128', help='Memory in Gb to be used for each node')
    parser.add_argument('--tasks', type=str, default='8', help='Number of tasks per node')
    parser.add_argument('--cpus_per_task', type=str, default='4', help='Number of cpus per task')
    args = parser.parse_args()
    return args

# def monitor_jobs(common_drop_directory, original_job_ids, directory_file_oh  = "running_directories.pkl", 
#                  file_extensions_oh=['jpg','gif'], username='dje4001', sleep = 60):
#     """ Find and monitor my jobs in the slurm queue  """

#     def find_my_jobs(original_job_ids,username='dje4001'):
#         squeue_result_oh = subprocess.run(f"squeue --noheader -u {username} --format=%A", shell=True, capture_output=True, text=True)
#         current_ids = squeue_result_oh.stdout.split()
#         running_jobs = [job for job in original_job_ids if job in current_ids]
#         if len(running_jobs)>0:
#             result = True
#         else:
#             result = False
#         return result, running_jobs
    
#     # Continously monitor jobs if running
#     running_jobs = original_job_ids
#     result, running_jobs = find_my_jobs(running_jobs)
#     while result:
#         # Wait for some down time to check again
#         time.sleep(sleep) 
        
#         # Gather data for common directory (such as images)
#         monitor(common_drop_directory, directory_file = directory_file_oh, currently_running=result, file_extensions=file_extensions_oh)
#         result, running_jobs = find_my_jobs(running_jobs)

if __name__=='__main__':
    # Parse command line inputs
    args = cli_parser()
    
    # Gather all data via managepath object 
    pathobj = managepaths(base_cell_count_path = args.parent_segmentation_path, 
                          base_stitched_image_path = args.parent_image_path,
                          base_registration_output_path = args.parent_registration_output_path)
    pathobj()

    # Send all data to sbatch
    joblist = submit_jobs(managepathobj = pathobj, 
                conda_environment_name = args.conda_environment_name, 
                partition_oh = args.partition, 
                email = args.user_email, 
                memory_per_job = args.memory, 
                tasks_per_job = args.tasks, 
                cpus_per_task = args.cpu_per_task)
    
    # Monitor jobs if succesful. 
    # monitor_jobs(pathobj.common_drop_directory, joblist, directory_file_oh  = "running_directories.pkl", 
    #              file_extensions_oh=['jpg','gif'], username='dje4001', sleep = 60)

    """
    Note regarding usage:

    To write a force flips file, force orientation file or align_binary_mask file,
    Use the following bash code in the drop path of interest:

    echo -e "12\n34\n56" > force_flips.txt

    Remember files must be spelled correctly to be used
    """
