import numpy as np
import pandas as pd

def quick_boot(input_array,number=15):
    return np.random.choice(input_array, number)

def quick_boot_df(df, n_boot=15, group_cols=['suid', 'group', 'regionname', 'lateralization'], value_col='rawcount'):
    # Sample subjects with replacement
    subjects = df['suid'].unique()
    sampled_suids = np.random.choice(subjects, size=n_boot, replace=True)

    # Recreate each sampled subject so repeated draws remain repeated in the bootstrap sample
    sampled_frames = []
    for draw_idx, suid in enumerate(sampled_suids):
        subject_rows = df[df['suid'] == suid].copy()
        if 'suid' in group_cols:
            subject_rows['suid'] = f'{suid}_boot{draw_idx}'
        sampled_frames.append(subject_rows)

    if not sampled_frames:
        return df.iloc[0:0].copy()

    df_sampled = pd.concat(sampled_frames, ignore_index=True)

    # Aggregate counts per group/region/side
    df_boot = df_sampled.groupby(group_cols, as_index=False).agg({value_col: 'sum'})

    return df_boot


class bootstrap:
    def __init__(self,data):
        self.data=data

    def sample(self,):
        return np.random.choice(self.data)

class hiearchical_bootstrap(bootstrap):
    def __init__(self,hiearchical_data):
        """ Data should be a list of lists.
        Ex. Group list -> Subject list -> number of cells for region of interest"""
        self.hiearchical_data=hiearchical_data

    def __call__(self):
        for level in range(len(self.hiearchical_data)):
            self.data=self.hiearchical_data[level]
            outsample=self.sample()
        return outsample

class simulation:
    def __init__(self,data,num_simulations=80):
        self.data=data
        self.num_simulations=num_simulations

    def run_hiearchiacal_bootstrap(self):
        final_dataset=[]
        for l in range(self.num_simulations):
            bsob = hiearchical_bootstrap(self.data)
            sample = bsob()
            final_dataset.append(sample)
        return final_dataset
