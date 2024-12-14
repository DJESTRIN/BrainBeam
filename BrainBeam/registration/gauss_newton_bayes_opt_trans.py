
import numpy as np
import os
import nrrd
import re
import ipdb
import nibabel as nib
from PIL import Image
from PIL import ImageFile

# Re-written custom functions/classes from cloudreg
from BrainBeam.registration.slice_view import slice_view


class set_up_registration():
    def __init__(self, 
                 base_path = '~/',
                 target_name = os.join.path('~/','autofluorescence_data.tif'),
                 registration_prefix = os.join.path('~/','registration/'),
                 atlas_prefix = os.join.path('~/','CloudReg/cloudreg/registration/atlases/'),
                 dxJ0=np.array([9.36, 9.36, 5]),
                 missing_data_correction = 1,
                 grid_correction = 0,
                 bias_correction = 0,
                 initial_affine = np.eye(4),
                 fixed_scale = np.array([1, 1, 1]),
                 sigmaR = 1e4,
                 niter = 5000,
                 eV = 1e6,
                 eA = 0.2,
                 nT = 10,
                 sigmaC = 5,
                 CA = 1, 
                 CB = -1,
                 order = 4,
                 nM = 1,
                 nMaffine = 1,
                 naffine =0,
                 a = 500, 
                 prior = np.array([0.79, 0.2, 0.01]),
                 do_GN = 1,
                 rigid_only = 0,
                 uniform_scale_only = 1,):
        """ Sets up registration. Class puts everything in place so that we can run registration  """

        self.base_path = base_path
        self.target_name = target_name
        self.registration_prefix = registration_prefix
        self.atlas_prefix = atlas_prefix
        self.dxJ0 = dxJ0

        self.missing_data_correction = missing_data_correction
        self.grid_correction = grid_correction
        self.bias_correction = bias_correction

        self.fixed_scale = fixed_scale * np.array([1, 1, 1])
        self.A = initial_affine
        self.eV = eV
        self.eA = eA

        # Non-changed attributes
        self.nT = nT
        self.sigmaC = sigmaC
        self.CA = CA
        self.CB = CB
        self.order = order
        self.nM = nM
        self.nMaffine = nMaffine
        self.naffine = naffine
        self.a = a
        self.prior = prior
        self.do_GN = do_GN
        self.rigid_only = rigid_only
        self.uniform_scale_only = uniform_scale_only

        self.A_lin = self.A[:3, :3].copy()
        self.A_lin[np.abs(self.A_lin) < np.min(np.max(np.abs(self.A_lin)))] = 0
        self.A_lin[np.abs(self.A_lin) > 0] = 1
        self.fixed_scale_r = self.A_lin.T @ fixed_scale.T

        if not np.all(fixed_scale == fixed_scale[0]):
            # fixed scale is nonuniform
            self.uniform_scale_only = 0
            # GN affine update can be unstable
            self.eA = 0.002

        # Note, these attributes do not really make sense to 
        # me in the original code but keeping for later
        self.downloop_start = 1
        self.downloop = 1
        self.prefix = self.registration_prefix

        self.template_name = os.path.join(self.atlas_prefix,'/atlas_data.nrrd')
        self.label_name = os.path.join(self.atlas_prefix,'/parcellation_data.nrrd')
        self.vname = ''
        self.Aname = ''
        self.coeffsname = ''

    def set_up_files(self):
        """ Set up any files and paths """
        # Rename prefix with downloop data
        filepath, filename = os.path.split(self.prefix)
        name, ext = os.path.splitext(filename)
        self.prefix = os.path.join(filepath, f"{name}downloop_{self.downloop}_{ext}")

        # Double check filepath folder exists
        filepath = os.path.dirname(self.prefix)
        if not os.path.exists(filepath):
            os.makedirs(filepath)

    def get_atlas_data(self):
        """ Put atlas data into correct formating """
        # Clean up and extract info from atlas (I)
        I, self.meta = nrrd.read(self.template_name) # Get array and meta data
        I = I.astype(float) # Convert to float
        spacedirections = self.meta['spacedirections']  # Get meta data from attribute
        directions = np.array(re.findall(r'\((\d+),(\d+),(\d+)\)', spacedirections), dtype=int)
        self.dxI = np.diag(directions.flatten()).T # calculate dxI
        npad = round(1000 / self.dxI[0]) # create a padding
        I = np.pad(I, ((npad, npad), (npad, npad), (npad, npad)), mode='constant', constant_values=0) # pad the atlas with zeros
        self.I = (I - np.mean(I))/np.std(I) #Normalize I array and set to attribute
        nxI = I.shape # Get shape

        # Get change in X, Y and Z axis sizing
        xI = np.arange(nxI[1]) * self.dxI[0]
        yI = np.arange(nxI[0]) * self.dxI[1]
        zI = np.arange(nxI[2]) * self.dxI[2]
        xI = xI - np.mean(xI) # Center coordinates
        yI = yI - np.mean(yI)
        zI = zI - np.mean(zI)
        self.XI, self.YI, self.ZI = np.meshgrid(xI, yI, zI) # Calculate mesh grid for I

        slice_view(xI,yI,zI,I) # Generate slice view image of atlas

        # Get Frequency grid and calculate mesh
        fxI = np.arange(0, len(xI)) / len(xI) / self.dxI[0]
        fyI = np.arange(0, len(yI)) / len(yI) / self.dxI[1]
        fzI = np.arange(0, len(zI)) / len(zI) / self.dxI[2]
        self.FXI, self.FYI, self.FZI = np.meshgrid(fxI, fyI, fzI)

    def get_label_data(self):
        """ Get label data and reformat """
        nrrd_data, meta = nib.nrrd.read(self.label_name)
        spacedirections = meta['space directions']  
        dxL = np.diag([spacedirections[i][i] for i in range(3)])
        npad = 1 
        self.L = np.pad(nrrd_data, pad_width=npad, mode='constant', constant_values=0)

    def convert_target_to_atlas(self):
        img = Image.open(self.target_name)

        # Get metadata
        info = {"Filename": self.target_name,
                "Format": img.format,
                "Width": img.width,
                "Height": img.height,
                "Mode": img.mode}

        self.down = np.round((self.dxI/self.dxJ0))


    def __call__(self):
        ipdb.set_trace()

class gauss_newton_registration(set_up_registration):
    def __init__(self):
        i=1

class perform_study():
    """
    """

if __name__=='__main__':
    