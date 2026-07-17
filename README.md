<h1> <b> 🔦 BrainBeam 🔦 </b> </h1> 
A generalized open-source pipeline and gui for analyzing light sheet brain tissue. 

<h2> <b> ⚠️ Warning: This code is still under development. ⚠️ </b> </h2>
Please kindly ignore any issues with code as well as any missing citations to others code. 

<h2> <b> Installation </b> </h2>

- Create a Python 3.9+ environment.
- Install the Python dependencies with `python -m pip install -r requirements.txt`.
- To install the package itself from the repository root, run `python -m pip install -e .`.

<h2> <b> Entry points </b> </h2>

- `Run_BrainBeam.sh` launches the local GUI entry point at `BrainBeam/gui/BrainBeam.py`.
- `pipeline_spinup.sh <scratch_directory> <store_start_directory> <store_finish_directory>` is the top-level SLURM submission script. It submits raw-data copy jobs, then starts the TIFF conversion/destriping/stitching chain through the bash scripts under `BrainBeam/`.
- The SLURM scripts assume a Linux cluster environment with `sbatch`, Bash, and the required Conda environments already available. They are not intended to run directly on Windows outside a Bash-compatible shell.
 <h2> <b> BrainBeam's Guided User Interface </b></h2>

 


<h2> <b> Example Classifier Performance </b></h2>
We trained an ilastik based classifier to quantify cell counts for whole-brain light-sheet data. In addition to training, models are enhanced through hyper-parameter tuning:


The overall performance of our models results in an F1 score >0.85:


Here is an example of our ilastik classifier's performance on a sagittal slice of brain tissue:


<h2> <b> References </b></h2>
Portions of this library utalize code from (or are inspired by) the following references:

- <b> De-striping: </b> Kirst, et al. (2020). Mapping the fine-scale organization and plasticity of the brain vasculature. Cell, 180(4), 780-795. https://doi.org/10.1016/j.cell.2020.01.028

- <b> De-striping: </b> Renier et al. (2016). Mapping of brain activity by automated volume analysis of immediate early genes. Cell, 165(7), 1789-1802. https://doi.org/10.1016/j.cell.2016.05.007

- <b> Stitching: </b> Bria, A., & Iannello, G. (2012). TeraStitcher - A tool for fast automatic 3D-stitching of teravoxel-sized microscopy images. BMC Bioinformatics, 13(1), 316. https://doi.org/10.1186/1471-2105-13-316

- <b> Cell Segmentation: </b> Athey, T. L., Wright, M. A., Pavlovic, M., Chandrashekhar, V., Deisseroth, K., Miller, M. I., & Vogelstein, J. T. (2023). BrainLine: An open pipeline for connectivity analysis of heterogeneous whole-brain fluorescence volumes. Neuroinformatics, 21(4), 637-639. https://doi.org/10.1007/s12021-023-09638-2

- <b> Cell Segmentation: </b> Berg, S., Kutra, D., Kroeger, T., Straehle, C. N., Kausler, B. X., Haubold, C., Schiegg, M., Ales, J., Beier, T., Rudy, M., Eren, K., Cervantes, J. I., Xu, B., Beuttenmueller, F., Wolny, A., Zhang, C., Koethe, U., Hamprecht, F. A., & Kreshuk, A. (2019). ilastik: Interactive machine learning for (bio)image analysis. Nature Methods. https://doi.org/10.1038/s41592-019-0582-9

- <b> Brain Registration: </b> Chandrashekhar, V., Tward, D. J., Crowley, D., et al. (2021). CloudReg: Automatic terabyte-scale cross-modal brain volume registration. Nature Methods, 18(8), 845–846. https://doi.org/10.1038/s41592-021-01218-z

<h2> <b> Contributions and citation </b> </h2>

- Code: David James Estrin 

- Data: David James Estrin, Christine Kuang

Please cite this git repository as Estrin, D.J., et al., (2025) BrainBeam: A generalized open-source pipeline and gui for analyzing light sheet brain tissue. unpublished if you use any code or intellectual property from it. Thank you!

