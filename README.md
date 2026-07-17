# lightsheet_cluster
Written by David James Estrin. If using this code, please kindly cite (Estrin et al., 2024 unpublished). This repository was written to analyze light sheet data on a SLURM based high performance cluster. Pieces of this pipeline originate from other code repositories which have been cited accordingly below.

The pipeline consists of the following steps: 
(1) Moving the data to a scratch drive
(2) Denoising/destriping the data via Pystripe (https://github.com/chunglabmit/pystripe)
(3) Stitching the data via terastitcher (https://github.com/abria/TeraStitcher)
(4) Registering images to allen brain atlas (https://github.com/neurodata/CloudReg)
(5) Segmenting pixels and counting cells (cells, axons, etc) (loosely based on brainlit: https://github.com/neurodata/brainlit  using ilastik: https://github.com/ilastik/ilastik). 
(6) calculating the number of counts per region, generating statistics and relevant pictures. 

## Statistics: LinReg

Automated statistical analysis (EDA, model-family selection, model fitting,
diagnostics, and reporting) is delegated to
[LinReg](https://github.com/DJESTRIN/LinReg), vendored here as a git submodule
at `external/LinReg`. LinReg is still under active development, so it is
pinned to a specific commit and consumed purely as a CLI subprocess (see
`statistics/linreg_bridge.py`) rather than imported as a library, keeping
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
