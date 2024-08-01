import pandas as pd
import os,glob
import argparse
import ipdb

def find_csv(path):
    pathsearch=path+'/*/*/*ities.csv'
    local_csvfiles = glob.glob(pathsearch,recursive=True)
    output_file=path+'/cell_counts.csv'
    return local_csvfiles,output_file

def concat_csv(files,outputfilename):
    csvfiles = []
    for filename in files:
        df = pd.read_csv(filename, index_col=None)
        csvfiles.append(df)

    finaldf = pd.concat(csvfiles, axis=0, ignore_index=True)
    finaldf.to_csv(outputfilename,index=False)
    return

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--input_dir')
    args=parser.parse_args()
    csvfiles,outputfilename=find_csv(args.input_dir)
    concat_csv(csvfiles,outputfilename)
