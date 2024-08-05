#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan  6 16:12:40 2023

@author: dje4001
"""
import cv2
import numpy as np
from matplotlib import pyplot as plt
import argparse
import glob
from multiprocessing import Pool

def ResizeWithAspectRatio(image, width=None, height=None, inter=cv2.INTER_AREA):
    dim = None
    (h, w) = image.shape[:2]

    if width is None and height is None:
        return image
    if width is None:
        r = height / float(h)
        dim = (int(w * r), height)
    else:
        r = width / float(w)
        dim = (width, int(h * r))

    return cv2.resize(image, dim, interpolation=inter)

def increase_brightness(img, value=1):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)

    lim = 255 - value
    v[v > lim] = 255
    v[v <= lim] += value

    final_hsv = cv2.merge((h, s, v))
    img = cv2.cvtColor(final_hsv, cv2.COLOR_HSV2BGR)
    return img

# Automatic brightness and contrast optimization with optional histogram clipping
def automatic_brightness_and_contrast(image, clip_hist_percent=1):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Calculate grayscale histogram
    hist = cv2.calcHist([gray],[0],None,[256],[0,256])
    hist_size = len(hist)
    
    # Calculate cumulative distribution from the histogram
    accumulator = []
    accumulator.append(float(hist[0]))
    for index in range(1, hist_size):
        accumulator.append(accumulator[index -1] + float(hist[index]))
    
    # Locate points to clip
    maximum = accumulator[-1]
    clip_hist_percent *= (maximum/100.0)
    clip_hist_percent /= 2.0
    
    # Locate left cut
    minimum_gray = 0
    while accumulator[minimum_gray] < clip_hist_percent:
        minimum_gray += 1
    
    # Locate right cut
    maximum_gray = hist_size -1
    while accumulator[maximum_gray] >= (maximum - clip_hist_percent):
        maximum_gray -= 1
    
    if maximum_gray==minimum_gray:
        auto_result=gray
        return (auto_result, 0,0)
    else:
        # Calculate alpha and beta values
        alpha = 255 / (maximum_gray - minimum_gray)
        beta = -minimum_gray * alpha
    
        auto_result = cv2.convertScaleAbs(image, alpha=alpha, beta=beta)
        return (auto_result, alpha, beta)

#image='/athena/listonlab/store/dje4001/lightsheet/puja_gcamp/raw/20220925_15_33_31_Cage_AnimalF83_VirusAAVrgNAcAAV1GCAMP7_PUJAPAREKH/20220925_15_33_31_Cage_AnimalF83_VirusAAVrgNAcAAV1GCAMP7_PUJAPAREKH/Ex_647_Em_680/'
#image='/athena/listonlab/store/dje4001/rsync_data/lightsheet/drop/2022_12_23/20221223_11_12_11_cage3976688_animal02_male_cohort3_fostrap2xai9tdtomato_tmtexperimental_0810_SingleSlice/Ex_647_Em_680_stitched/647.tif'
def auto_contrast(image):
    image1=cv2.imread(image)
    image1 = increase_brightness(image1, value=1)
    auto_result, alpha, beta = automatic_brightness_and_contrast(image1)
    cv2.imwrite(image,auto_result) #write over the raw data with auto contrasted image. 
    print(image)
    return auto_result

parser=argparse.ArgumentParser()
parser.add_argument("--input_path",type=str,required=True)

if __name__=="__main__":
    args=parser.parse_args()
    imagelist=glob.glob(args.input_path+'/**/*.tif*',recursive=True)
    with Pool() as p:
        p.map(auto_contrast,imagelist)
    
    """  Debugging """
    input_path='/athena/listonlab/store/dje4001/lightsheet/puja_gcamp/raw/20220925_15_33_31_Cage_AnimalF83_VirusAAVrgNAcAAV1GCAMP7_PUJAPAREKH/20220925_15_33_31_Cage_AnimalF83_VirusAAVrgNAcAAV1GCAMP7_PUJAPAREKH/Ex_647_Em_680/'
    imagelist=glob.glob(input_path+'/**/*.tif*',recursive=True)
        
        


