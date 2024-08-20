#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: bayes_registration.py
Description: This code utalizes scripts from the CloudReg package. Here, I use bayesian optimization to find the best hyperparameters (degrees/size) that
    produce the lowest Energy for registration. The primary point of this script is to fully automate the registration pipeline. 
Author: David Estrin
Date: 2024-08-19
Version: 1.0
"""
# Import packages
from .util import get_reorientations, aws_cli
from .visualization import (ara_average_data_link,ara_annotation_data_link,create_viz_link,S3Url,)
from .download_data import download_data
from .ingest_image_stack import ingest_image_stack
import shlex
from cloudvolume import CloudVolume
from scipy.spatial.transform import Rotation
import numpy as np
import argparse
import subprocess
import os
import shutil
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel as C
from scipy.optimize import minimize
import ipdb

# To do: skip downloading data if it is already a file...

class BayesOptRegistration:
    def __init__(self,input_s3_path,atlas_s3_path,parcellation_s3_path,atlas_orientation,output_s3_path,log_s3_path,orientation,fixed_scale,translation,
        rotation,missing_data_correction,grid_correction,bias_correction,regularization,num_iterations,registration_resolution,
        base_path="/athena/listonlab/scratch/dje4001/lightsheet_scratch/cloudreg_base/",bayesopt=True,init_samplesize=5):
        # Cloud Reg default parameters
        self.input_s3_path=input_s3_path
        self.atlas_s3_path=atlas_s3_path
        self.parcellation_s3_path=parcellation_s3_path
        self.atlas_orientation=atlas_orientation
        self.output_s3_path=output_s3_path
        self.log_s3_path=log_s3_path
        self.orientation=orientation
        self.fixed_scale=fixed_scale
        self.translation=translation
        self.rotation=rotation
        self.missing_data_correction=missing_data_correction
        self.grid_correction=grid_correction
        self.bias_correction=bias_correction
        self.regularization=regularization
        self.num_iterations=num_iterations
        self.registration_resolution=registration_resolution
        self.base_path = base_path

        # Bayes optimization parameters
        self.bayesopt=bayesopt
        self.init_samplesize=init_samplesize

    def initbayesopt(self):
        ipdb.set_trace()
        kernel = C(1.0, (1e-3, 1e3)) * RBF(length_scale=np.ones(4), length_scale_bounds=(1e-2, 1e2))
        self.gp = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=10, alpha=1e-2)
        self.hyperparameters = np.hstack((np.random.uniform(-40, 40, size=(self.init_samplesize,3)), np.random.uniform(0.8, 1.4, size=(self.init_samplesize, 1))))
        self.Energy = np.array([self.quick_register(x) for x in self.hyperparameters]).reshape(-1, 1) # Generate a few initial samples comparion hyperparameters to energy

    def upper_confidence_bound_acquisition(self, params, kappa=2.576):
        mean, std = self.gp.predict(params.reshape(1, -1), return_std=True)
        return mean - kappa * std

    def get_affine_matrix(self,translation,rotation,from_orientation,to_orientation,fixed_scale,s3_path,center=False,):
        vol = CloudVolume(s3_path)
        vol_size = np.multiply(vol.scales[0]["size"], vol.scales[0]["resolution"]) / 1e3
        affine = np.zeros((4, 4))
        affine[-1, -1] = 1
        order, flips = get_reorientations(from_orientation, to_orientation)
        vol_size = vol_size[order]
        dim = affine.shape[0]
        affine[range(len(order)), order] = 1
        affine[:3, :3] = np.diag(flips) @ affine[:3, :3]

        if center:
            affine[:3, -1] += np.array([vol_size[i] if flips[i] == -1 else 0 for i in range(len(flips))])
            affine[:3, -1] -= vol_size / 2

        # get rotation matrix
        if np.array(rotation).any():
            rotation_matrix = np.eye(4)
            rotation_matrix[:3, :3] = Rotation.from_euler("xyz", rotation, degrees=True).as_matrix()
            affine = rotation_matrix @ affine
        affine[:3, -1] += translation

        # scale by fixed_scale
        if isinstance(fixed_scale, float):
            affine = np.diag([fixed_scale, fixed_scale, fixed_scale, 1.0]) @ affine
        elif isinstance(fixed_scale, (list, np.ndarray)) and len(fixed_scale) == 3:
            affine = np.diag([fixed_scale[0], fixed_scale[1], fixed_scale[2], 1.0]) @ affine 
        else:
            affine = np.diag([fixed_scale[0], fixed_scale[0], fixed_scale[0], 1.0]) @ affine
        return affine

    def register(self):
        # Get volume information
        s3_url = S3Url(self.input_s3_path)
        channel = s3_url.key.split("/")[-1]
        exp = s3_url.key.split("/")[-2]

        # Set up paths and get info
        self.registration_prefix = f"{self.base_path}/{exp}_{channel}_registration/"
        self.atlas_prefix = f'{self.base_path}/CloudReg/cloudreg/registration/atlases/'
        self.target_name = f"{self.base_path}/{exp}_{channel}_autofluordata/autofluorescence_data.tif"
        atlas_name = f"{self.atlas_prefix}/atlas_data.nrrd"
        parcellation_name = f"{self.atlas_prefix}/parcellation_data.nrrd"
        parcellation_hr_name = f"{self.atlas_prefix}/parcellation_data.tif"

        # Download autoflourescent channel
        print("downloading input data for registration...")
        self.registration_resolution *= 1000.0 
        self.voxel_size = download_data(self.input_s3_path, self.target_name, 15000)
        _ = download_data(self.atlas_s3_path, atlas_name, self.registration_resolution, resample_isotropic=True)
        _ = download_data(self.parcellation_s3_path, parcellation_name, self.registration_resolution, resample_isotropic=True)
        self.parcellation_voxel_size, self.parcellation_image_size = download_data(self.parcellation_s3_path, parcellation_hr_name, 10000, return_size=True)

        # Calculate affine matrix
        initial_affine = self.get_affine_matrix(self.translation,self.rotation,self.atlas_orientation,self.orientation,self.fixed_scale,self.atlas_s3_path,)
        self.affine_string = [", ".join(map(str, i)) for i in initial_affine]
        self.affine_string = "; ".join(self.affine_string)

    def build_matlab_command(self):
        if self.bayesopt:
            bayesoptflag=1
            self.matlab_command = (
                f"matlab -nodisplay -nosplash -nodesktop -r \""
                f"niter={self.num_iterations};"
                f"sigmaR={self.regularization};"
                f"missing_data_correction={int(self.missing_data_correction)};"
                f"grid_correction={int(self.grid_correction)};"
                f"bias_correction={int(self.bias_correction)};"
                f"base_path='{self.base_path}';"
                f"target_name='{self.target_name}';"
                f"registration_prefix='{self.registration_prefix}';"
                f"atlas_prefix='{self.atlas_prefix}';"
                f"dxJ0={self.voxel_size};"
                f"fixed_scale={self.fixed_scale};"
                f"initial_affine=[{self.affine_string}];"
                f"parcellation_voxel_size={self.parcellation_voxel_size};"
                f"parcellation_image_size={self.parcellation_image_size};"
                f"BayesOptFlag={bayesoptflag};"
                f"run('~/CloudReg/cloudreg/registration/guass_newton_bayes_opt.m'); exit;\"")
        else:
            self.matlab_command = (
                f"matlab -nodisplay -nosplash -nodesktop -r \""
                f"niter={self.num_iterations};"
                f"sigmaR={self.regularization};"
                f"missing_data_correction={int(self.missing_data_correction)};"
                f"grid_correction={int(self.grid_correction)};"
                f"bias_correction={int(self.bias_correction)};"
                f"base_path='{self.base_path}';"
                f"target_name='{self.target_name}';"
                f"registration_prefix='{self.registration_prefix}';"
                f"atlas_prefix='{self.atlas_prefix}';"
                f"dxJ0={self.voxel_size};"
                f"fixed_scale={self.fixed_scale};"
                f"initial_affine=[{self.affine_string}];"
                f"parcellation_voxel_size={self.parcellation_voxel_size};"
                f"parcellation_image_size={self.parcellation_image_size};"
                f"run('~/CloudReg/cloudreg/registration/guass_newton_bayes_opt.m'); exit;\"")

    def run_matlab(self,command):
        subprocess.run(shlex.split(command))

    def run_BayesOpt(self,n_iterations=15):
        """ Run loop to optimize hyperparameters"""
        for i in range(n_iterations):
            # Fit hyper parameters to energy
            self.gp.fit(self.hyperparameters, self.Energy) #Fit gaussian processor

            def min_obj(params):
                return self.upper_confidence_bound_acquisition(params, self.gp)

            res = minimize(min_obj,np.random.uniform([-40]*6 + [0], [40]*6 + [10]), bounds=[(-40, 40)]*6 + [(0, 10)], method='L-BFGS-B')
            hyperparameters_next = res.x

            # Update MATLAB command, Run MATLAB command and grab energy output
            Energy_next = self.quick_register(hyperparameters_next)

            # Concat current hyperparmeters and energy to entire list
            self.hyperparameters = np.vstack((self.hyperparameters, hyperparameters_next))
            self.Energy = np.vstack((self.Energy, Energy_next))

            print(f"Iteration {i+1}: Hyperparameters = {hyperparameters_next}, Final Energy = {Energy_next}")

        # Grab the best hyper parameters
        self.final_hyperparameters = self.hyperparameters[np.argmin(self.Energy)]

    def quick_register(self,parameters_oh):
        # Break up current parameters and place into correct variables
        ipdb.set_trace()
        xrotation,yrotation,zrotation,scale=parameters_oh
        self.rotation=[xrotation,yrotation,zrotation]
        self.fixed_scale=scale

        # Set up registration
        self.register()
        self.build_matlab_command()
        self.run_matlab(self.matlab_command)
        Energy_oh = self.read_energy_result()
        return Energy_oh
    
    def read_energy_result(self):
        with open('energy_result.txt', 'r') as file:
            energy_value = float(file.readline().strip())
        return np.array(energy_value)


    def final_register(self):
        # Set up final parameters
        xrotation,yrotation,zrotation,scale=self.final_hyperparameters
        self.rotation=[xrotation,yrotation,zrotation]
        self.fixed_scale=scale

        # Set tuning to off
        self.bayesopt=False

        # Set up registration
        self.register()
        self.build_matlab_command()
        self.run_matlab(self.matlab_command)
    
    def forward(self):
        # Initialize and run tuning
        self.initbayesopt()
        self.run_BayesOpt()

        # Run final registration
        self.final_register()

def main():
    parser = argparse.ArgumentParser("Run CloudReg pipeline locally will Bayesian optimization")

    # Parse command line input arguments 
    parser.add_argument("--input_s3_path",help="S3 path to precomputed volume used to register the data",type=str,)
    parser.add_argument("--log_s3_path",help="S3 path at which registration outputs are stored.",type=str,)
    parser.add_argument("--output_s3_path",help="Output path",type=str,default=None,)
    parser.add_argument("--atlas_s3_path",help="Allen Reference atlas path",type=str,default=ara_average_data_link(100),)
    parser.add_argument("--parcellation_s3_path",help="Default is Allen Reference atlas parcellations path",type=str,default=ara_annotation_data_link(10),)
    parser.add_argument("--atlas_orientation",help="3-letter orientation of data. i.e. LPS",type=str,default='PIR')
    parser.add_argument("--orientation", help="3-letter orientation of data. i.e. LPS", type=str)
    parser.add_argument("--fixed_scale",help="Fixed scale of data, uniform in all dimensions. Default is 1.",nargs='+',type=float,default=[1.0, 1.0, 1.0])
    parser.add_argument("--translation",help="Initial translation in x,y,z respectively in microns.",nargs="+",type=float,default=[0, 0, 0],)
    parser.add_argument("--rotation",help="Initial rotation in x,y,z respectively in degrees.",nargs="+",type=float,default=[0, 0, 0],)
    parser.add_argument("--bias_correction",help="Perform bias correction prior to registration.",type=eval,choices=[True, False],default='True',)
    parser.add_argument("--missing_data_correction",help="Perform missing data correction",type=eval, choices=[True, False], default='True',)
    parser.add_argument("--grid_correction",help="Perform correction for low-intensity grid artifact",type=eval,choices=[True, False],default='False',)
    parser.add_argument("--regularization",help="Weight of the regularization. Bigger regularization means less regularization.",type=float,default=5e3,)
    parser.add_argument("--iterations",help="Number of iterations to do at low resolution. Default is 5000.",type=int,default=3000,)
    parser.add_argument("--registration_resolution",help="Minimum resolution that the registration is run at (in microns).",type=int,default=100,)
    args = parser.parse_args()

    # Run Registration with Bayes Optimization:
    reg_obj = BayesOptRegistration(args.input_s3_path,args.atlas_s3_path,args.parcellation_s3_path,args.atlas_orientation,args.output_s3_path,args.log_s3_path,args.orientation,
        args.fixed_scale,args.translation,args.rotation,args.missing_data_correction,args.grid_correction,args.bias_correction,args.regularization,args.iterations,
        args.registration_resolution)
    
    reg_obj.forward()

if __name__ == "__main__":
    main()
