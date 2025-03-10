#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: concatdataframe.py
Description: 
Author: David Estrin
Date: 2024-008-15
Version: 1.0
"""
import pandas as pd

file1=r'C:\Users\listo\communal_registration_logcal_drop\water\df_tall.csv'
file2=r'C:\Users\listo\communal_registration_logcal_drop\tmt\df_tall.csv'

waterdf = pd.read_csv(file1)
tmtdf = pd.read_csv(file2)

finaldf=pd.concat([waterdf,tmtdf],ignore_index=True)
finaldf.to_csv(r'C:\Users\listo\communal_registration_logcal_drop\tmtexperiment.csv',index=False)
