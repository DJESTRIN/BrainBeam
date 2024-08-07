import numpy as np

def quick_boot(input_array,number=100):
    return np.random.choice(input_array, 100)

class bootstrap:
    def __init__(self,data):
        self.data=data
        random_sample = self.sample()
        return random_sample

    def sample(self,):
        return np.random.choice(self.data)

class hiearchical_bootstrap(bootstrap):
    def __init__(self,hiearchical_data):
        """ Data should be a list of lists.
        Ex. Group list -> Subject list -> number of cells for region of interest"""
        self.hiearchical_data=hiearchical_data

    def __call__(self):
        for level in len(self.hiearchical_data):
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

