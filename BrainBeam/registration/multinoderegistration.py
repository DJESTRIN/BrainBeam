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
from BrainBeam.registration.monitorprocess import monitor
from BrainBeam.registration.monitorprocess import extract_path_info as epi

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
            self.base_registration_output_path = os.path.join(parent_folder,"registration")
        else:
            self.base_registration_output_path = base_registration_output_path

        if not os.path.exists(self.base_registration_output_path):
            os.mkdir(self.base_registration_output_path)


        """ Create manage_paths. Here are details regarding this dictionary
            (1) image_folder
            (2) cell_counts_files
            (3) atlas_drop_path
            (4) registration_drop_path
            (5) communal_drop_path
            (6) base_registration_output_path
            (7) force_flips
            (8) force_orientations
            (9) align_binary_mask
            (10) communal_slurm_log_directory
            (11) communal_slurm_error_directory """
        self.manage_paths = {}


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
        return epi(path_oh)

    def align_files_to_folders(self):
        # Loop over all image folders and csv files to find matches
        # Place all matches in a dictrionary
        for folders_oh in self.image_folders:
            folder_oh_cage, folder_oh_subject = self.extract_path_info(folders_oh)
            matches = []

            for file_oh in self.cell_count_files:
                file_oh_cage, file_oh_subject = self.extract_path_info(file_oh)
                
                if folder_oh_cage == file_oh_cage and folder_oh_subject == file_oh_subject:
                    matches.append(file_oh)

            if matches:
                key = f'{folder_oh_cage} {folder_oh_subject}'
                self.manage_paths[key] = {'image_folder': folders_oh,
                                                        'cell_count_files': matches}

    def set_registration_outputs(self):
        """ Set up output folders for registration """
        for folders_oh in self.image_folders:
            folder_oh_cage, folder_oh_subject = self.extract_path_info(folders_oh)
            output_folder_base = os.path.join(self.base_registration_output_path,f"{folder_oh_cage}_{folder_oh_subject}_registration")

            # Make the base folder for current subject
            if not os.path.exists(output_folder_base):
                os.mkdir(output_folder_base)

            # Make atlas drop path
            output_folder_base_atlas = os.path.join(output_folder_base,"atlas")
            if not os.path.exists(output_folder_base_atlas):
                os.mkdir(output_folder_base_atlas)

            # Make registration drop path 
            output_folder_base_dropoh = os.path.join(output_folder_base,"registration_drop")
            if not os.path.exists(output_folder_base_dropoh):
                os.mkdir(output_folder_base_dropoh)

            # Create common folder where figures are copied to for quick viewing
            communal_drop_folder = os.path.join(self.base_registration_output_path,"communal_figures")
            if not os.path.exists(communal_drop_folder):
                os.mkdir(communal_drop_folder)

            # Add drop paths to dictionary
            folder_oh_cage, folder_oh_subject = self.extract_path_info(folders_oh)
            key = f'{folder_oh_cage} {folder_oh_subject}'
            self.manage_paths[key] = {'atlas_drop_path': output_folder_base_atlas,
                                                    'registration_drop_path': output_folder_base_dropoh,
                                                    'communal_drop_folder': communal_drop_folder,
                                                    'base_registration_output_path':self.base_registration_output_path}

            # Save a list of output folders to be monitored by other code
            runningdirsfile = os.path.join(communal_drop_folder, "running_directories.pkl")
            if os.path.exists(runningdirsfile):
                with open(runningdirsfile, "rb") as f:
                    registration_drop_paths = pickle.load(f)
            else:
                registration_drop_paths = []

            registration_drop_paths.append(self.manage_paths[key]['registration_drop_path'])

            with open(runningdirsfile, "wb") as f:
                pickle.dump(registration_drop_paths, f)

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
        for subject, variables in self.manage_paths.items():
            cell_count_files = variables.get('cell_count_files', [])
            registration_drop_path = variables.get('registration_drop_path', '')

            for file in cell_count_files:
                channel_oh = self.determine_channel(file)
                assert channel_oh is not None
                shutil.copy2(file, os.path.join(registration_drop_path,f"{subject}_channel{channel_oh}_cell_counts.csv"))


    def load_force_flips(self):
        """ find force flips file and load if present """
        for subject, variables in self.manage_paths.items():
            registration_drop_path = variables.get('registration_drop_path', '')
            if os.path.exists(os.path.join(registration_drop_path,"force_flips.txt")):
                with open(os.path.join(registration_drop_path,"force_flips.txt"), 'r') as file:
                    force_flips = ' '.join(str(int(line.strip())) for line in file)
                self.manage_paths[subject]['force_flips'] = force_flips
            
            else:
                self.manage_paths[subject]['force_flips'] = None

           
    def load_force_orientations(self):
        """ find force flips file and load if present """
        for subject, variables in self.manage_paths.items():
            registration_drop_path = variables.get('registration_drop_path', '')
            if os.path.exists(os.path.join(registration_drop_path,"force_orientations.txt")):
                with open(os.path.join(registration_drop_path,"force_orientations.txt"), 'r') as file:
                    force_orientations = ' '.join(str(int(line.strip())) for line in file)
                self.manage_paths[subject]['force_orientations'] = force_orientations
            
            else:
                self.manage_paths[subject]['force_orientations'] = None
    
    def load_align_binary_mask_file(self):
        """ find force flips file and load if present """
        for subject, variables in self.manage_paths.items():
            registration_drop_path = variables.get('registration_drop_path', '')
            if os.path.exists(os.path.join(registration_drop_path,"align_binary_mask.txt")):
                with open(os.path.join(registration_drop_path,"align_binary_mask.txt"), 'r') as file:
                    binary_mask_align = ' '.join(str(int(line.strip())) for line in file)
                self.manage_paths[subject]['align_binary_mask'] = binary_mask_align
            
            else:
                self.manage_paths[subject]['align_binary_mask'] = None


    def set_slurm_output_folders(self):
        """ Create output folders where slurm log and error data will be stored for ease of use """
        for subject, variables in self.manage_paths.items():
            base_output_path = variables.get('base_registration_output_path', '')

            # Create folders if they do not exist
            communal_slurm_log_directory = os.path.join(base_output_path,"slurm_logs")
            communal_slurm_error_directory = os.path.join(base_output_path,"slurm_errors")
            if not os.path.exists(communal_slurm_log_directory):
                os.mkdir(communal_slurm_log_directory)
            if not os.path.exists(communal_slurm_error_directory):
                os.mkdir(communal_slurm_error_directory)

            # Add to dictionary
            self.manage_paths[subject]['communal_slurm_log_directory'] = communal_slurm_log_directory
            self.manage_paths[subject]['communal_slurm_error_directory'] = communal_slurm_error_directory

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
    for subject, variables in managepathobj.manage_paths.items():
        ipdb.set_trace()
        # Pull data from dictionary via get
        communal_slurm_log_directory = variables.get(subject, {}).get('communal_slurm_log_directory', '')
        communal_slurm_error_directory = variables.get(subject, {}).get('communal_slurm_error_directory', '')
        image_folder = variables.get(subject, {}).get('image_folder', '')
        atlas_drop_path = variables.get(subject, {}).get('atlas_drop_path', '')
        registration_drop_path = variables.get(subject, {}).get('registration_drop_path', '')
        align_binary_mask = variables.get(subject, {}).get('align_binary_mask', '')
        force_orientations = variables.get(subject, {}).get('force_orientations', '')
        force_flips = variables.get(subject, {}).get('force_flips', '')
        
        # Build command line interface command
        my_command = f"sbatch --job-name=merge_data_to_tallformat \
                --mem={memory_per_job}G \
                --ntasks={tasks_per_job} \
                --cpus-per-task={cpus_per_task} \
                --partition={partition_oh} \
                --mail-type=BEGIN,END,FAIL \
                --mail-user={email} \
                --output={communal_slurm_log_directory}/%x-%j.out \
                --error={communal_slurm_error_directory}/%x-%j.err \
                --wrap='source ~/.bashrc && conda activate {conda_environment_name} && python ./registration.py \
                --image_path {image_folder} \
                --atlas_path {atlas_drop_path} \
                --output_path {registration_drop_path} \
                --full_output_path \
                --align_binary_mask {align_binary_mask} \
                --force_orientation {force_orientations} \
                --force_flips {force_flips}'"
        ipdb.set_trace()
        # Run subprocess on command and pull out result. 
        result = subprocess.run([my_command], shell=True, capture_output=True, text=True)
        
        # Append job id to list for monitoring
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

def monitor_jobs(common_drop_directory, original_job_ids, directory_file_oh  = "running_directories.pkl", 
                 file_extensions_oh=['jpg','gif'], username='dje4001', sleep = 60):
    """ Find and monitor my jobs in the slurm queue  """

    def find_my_jobs(original_job_ids,username='dje4001'):
        squeue_result_oh = subprocess.run(f"squeue --noheader -u {username} --format=%A", shell=True, capture_output=True, text=True)
        current_ids = squeue_result_oh.stdout.split()
        running_jobs = [job for job in original_job_ids if job in current_ids]
        if len(running_jobs)>0:
            result = True
        else:
            result = False
        return result, running_jobs
    
    # Continously monitor jobs if running
    running_jobs = original_job_ids
    result, running_jobs = find_my_jobs(running_jobs)
    while result:
        # Wait for some down time to check again
        time.sleep(sleep) 
        
        # Gather data for common directory (such as images)
        monitor(common_drop_directory, directory_file = directory_file_oh, currently_running=result, file_extensions=file_extensions_oh)
        result, running_jobs = find_my_jobs(running_jobs)

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
                cpus_per_task = args.cpus_per_task)
    
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
