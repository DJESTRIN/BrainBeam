<h1> <b> 🔦 BrainBeam 🔦 </b> </h1> 
A generalized open-source pipeline and gui for analyzing light sheet brain tissue. 

<h2> <b> Pipeline Overview </b> </h2>

The pipeline consists of the following steps:
1. Moving the data to a scratch drive.
2. Denoising/destriping the data via Pystripe (https://github.com/chunglabmit/pystripe).
3. Stitching the data via TeraStitcher (https://github.com/abria/TeraStitcher).
4. Registering images to the Allen brain atlas (https://github.com/neurodata/CloudReg).
5. Segmenting pixels and counting cells (cells, axons, etc), loosely based on brainlit (https://github.com/neurodata/brainlit) using ilastik (https://github.com/ilastik/ilastik).
6. Calculating the number of counts per region, generating statistics and relevant figures.

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

<h2> <b> Running with Docker </b> </h2>

BrainBeam now includes a root-level `Dockerfile` for reproducible local/standalone execution without manually recreating the Python + system library stack.

Build the image from the repository root:

```bash
docker build -t brainbeam .
```

Run the container with a host directory mounted for your raw data and outputs. Keep large lightsheet datasets on the host filesystem rather than copying them into the image:

```bash
docker run --rm -it -v /path/to/lightsheet-data:/data brainbeam
```

Inside the container, the BrainBeam source lives at `/opt/brainbeam` and your mounted dataset is available at `/data`. The container intentionally drops you into a shell in the fully provisioned environment because the repository currently contains multiple stage-specific entry scripts rather than one container-safe universal launcher. From that shell you can launch the Python pipeline components you need against the mounted volume.

The Docker image is intentionally focused on the Python image-processing pipeline. The `BrainBeam/statistics` folder contains R / R Markdown analyses, but those are better treated as optional post-processing in a separate R-based environment or companion image rather than bundled into the main runtime image.

Important: the SLURM submission/orchestration scripts (for example the various `*_spinup.sh` files and `pipeline_spinup.sh`) are intended for direct HPC cluster use and are **not** meant to run inside this container. Use the container for the local/standalone execution path, and continue to use the native cluster environment for SLURM-based workflows.

<h2> <b> Running on HPC with Singularity/Apptainer </b> </h2>

Most HPC/SLURM clusters run Singularity or its drop-in successor Apptainer instead of Docker, since Docker needs a root-owned daemon that isn't available to regular cluster users. `Singularity.def` at the repository root mirrors the `Dockerfile` (same base image, same system packages, same Python install), so the same environment can be built as a `.sif` image for cluster use.

Build the image (from a login/build node or your own workstation that has fakeroot/sudo access - this step usually can't run on a compute node reached via `srun`/`sbatch`):

```bash
bash build_singularity.sh          # writes brainbeam.sif next to Singularity.def
```

If `--fakeroot` isn't permitted for your account, `build_singularity.sh` prints the alternatives (asking cluster admins to enable it, building on your own machine and copying `brainbeam.sif` up, or using a remote build service).

Once built, run a pipeline step reproducibly inside the image, with your scratch directory bind-mounted in:

```bash
singularity exec --bind /path/to/scratch:/data brainbeam.sif python /opt/brainbeam/BrainBeam/destripe/destripe.py --help
```

or drop into an interactive shell the same way the Docker image does:

```bash
singularity shell --bind /path/to/scratch:/data brainbeam.sif
```

As with the Docker image, the `*_spinup.sh`/`pipeline_spinup.sh` SLURM orchestration scripts are meant to run natively on the cluster (they call `sbatch` themselves) - use the `.sif` image to run individual pipeline stages consistently from inside an sbatch job step rather than wrapping the orchestration scripts themselves.

<h2> <b> Statistics: LinReg </b> </h2>

Automated statistical analysis (EDA, model-family selection, model fitting,
diagnostics, and reporting) is delegated to
[LinReg](https://github.com/DJESTRIN/LinReg), vendored here as a git submodule
at `external/LinReg`. LinReg is still under active development, so it is
pinned to a specific commit and consumed purely as a CLI subprocess (see
`BrainBeam/statistics/linreg_bridge.py`) rather than imported as a library, keeping
BrainBeam decoupled from LinReg's internal API.

Setup:

```bash
git submodule update --init --recursive
pip install -e external/LinReg/python
Rscript external/LinReg/R/install_packages.R
```

Update the pinned version deliberately when LinReg stabilizes new features:

```bash
cd external/LinReg
git fetch origin
git checkout <new-commit-or-tag>
cd ../..
git add external/LinReg
git commit -m "Bump LinReg submodule to <new-commit-or-tag>"
```

