import glob,os
import cv2
import numpy as np
import ipdb
import tqdm

inputfolder="C:/Users/listo/data/syglass_atlas_fullres/20220926_17_49_34_CAGE4094795_ANIMAL01_VIRUSRABIES_CORTEXPERIMENTAL/tiffsequence/"
dropfolder="C:\\Users\\listo\\data\\syglass_atlas_fullres\\20220926_17_49_34_CAGE4094795_ANIMAL01_VIRUSRABIES_CORTEXPERIMENTAL\\tiffsequence_uint16\\"

os.chdir(inputfolder)
images=glob.glob("*.tif*")
for image in tqdm.tqdm(images):
    imoh=cv2.imread(image,-1)
    imoh=np.asarray(imoh).astype(np.uint16)
    os.chdir(dropfolder)
    cv2.imwrite(image,imoh)
    os.chdir(inputfolder)