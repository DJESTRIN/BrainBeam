# lightsheet_cluster
Written by David James Estrin. If using this code, please kindly cite (Estrin et al., 2024 unpublished). This repository was written to analyze light sheet data on a SLURM based high performance cluster. Pieces of this pipeline originate from other code repositories which have been cited accordingly below.

The pipeline consists of the following steps: 
(1) Moving the data to a scratch drive
(2) Denoising/destriping the data via Pystripe (https://github.com/chunglabmit/pystripe)
(3) Stitching the data via terastitcher (https://github.com/abria/TeraStitcher)
(4) Registering images to allen brain atlas (https://github.com/neurodata/CloudReg)
(5) Segmenting pixels and counting cells (cells, axons, etc) (loosely based on brainlit: https://github.com/neurodata/brainlit  using ilastik: https://github.com/ilastik/ilastik). 
(6) calculating the number of counts per region, generating statistics and relevant pictures. 
