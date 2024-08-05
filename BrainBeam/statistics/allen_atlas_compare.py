import pandas as pd
import numpy as np
import ipdb
import matplotlib.pyplot as plt 
from matplotlib_venn import venn2

class get_brain_regions():
    def __init__(self,data_path,allen_path):
        self.data=pd.read_csv(data_path) # my data
        self.allen=pd.read_csv(allen_path) #allen inst data
        self.maxiou=0
        self.stop=False

    def tresh_analysis(self):
        all_levels=['lv1','lv2','lv3','lv4','lv5','lv6','lv7','lv8','lv9','lv10']
        global_list=[]
        for level in all_levels:
            self.aggregated=self.data.groupby([level], as_index=False)['n'].sum()
            local_list=[]
            for thresh in range(100):
                IOUoh=self.threshold_regions(level,thresh)
                local_list.append(IOUoh)
                if self.stop:
                    return
            global_list.append(np.asarray(local_list))
        
        self.global_list=np.asarray(global_list)
        return
    
    def plot_IOU_results(self):
        all_levels=['lv1','lv2','lv3','lv4','lv5','lv6','lv7','lv8','lv9','lv10','highest']
        plt.figure(figsize=(10,10))
        for heirch in self.global_list:
            plt.plot(heirch,linewidth=7)
        plt.plot(0,0.37604456824512533,'rx',markersize=20,linewidth=10)
        plt.legend(all_levels, loc="upper right")
        plt.ylabel('Intersection over Union')
        plt.xlabel('Cell Threshold')
        plt.savefig('Thresholding_Allen_analysis.pdf') 
        return
    
    def threshold_regions(self,level,threshold):
        threshold+=1
        self.aggregated = self.aggregated.drop(self.aggregated[self.aggregated.n < threshold].index)
        dataregions=self.aggregated[level]
        allenregions=self.allen['structure-name']
        dataregions=dataregions.to_numpy()
        allenregions=allenregions.to_numpy()
        dataregions=np.unique(dataregions)
        allenregions=np.unique(allenregions)
        dhits,dmisses,ahits,amisses=self.get_stats(allenregions,dataregions)
        intersection=dhits
        union=dhits+dmisses+amisses
        IOU=intersection/union
        print(f'Threshold: {threshold} , Intersection over Union: {IOU}')
        if IOU>self.maxiou:
            self.maxiou=IOU

        if IOU>0.87604456824512530:
            print(f'This is the best level: {level}, this is the best threshold: {threshold}')
            self.vendiagram(dmisses,amisses,dhits,'thresholded_diagram.pdf')
            self.stop=True
        return IOU

    def get_regions(self):
        dataregions=self.data[f'lv7']
        allenregions=self.allen['structure-name']
        dataregions=dataregions.to_numpy()
        allenregions=allenregions.to_numpy()
        dataregions=np.unique(dataregions)
        allenregions=np.unique(allenregions)
        dhits,dmisses,ahits,amisses=self.get_stats(allenregions,dataregions)
        intersection=dhits/(dhits+dmisses)
        union=dhits+dmisses+amisses
        IOU=intersection/union
        print(f'All data inersection: {IOU}')
        self.vendiagram(dmisses,amisses,dhits,'allsubjects.pdf')

    def get_stats(self,regions1,regions2):
        #Loop through allen data and find hits and misses
        ahits=0
        amisses=0
        for region in regions1:
            aroh=np.where(regions2==region)
            if aroh[0].size==0:
                amisses+=1
            else:
                ahits+=1

        #Loop through our data and find hits and misses
        dhits=0
        dmisses=0
        for region in regions2:
            aroh=np.where(regions1==region)
            if aroh[0].size==0:
                dmisses+=1
            else:
                dhits+=1

        return dhits,dmisses,ahits,amisses
    
    def vendiagram(self,dmisses,amisses,dhits,filename):
        # Use the venn2 function
        plt.figure(figsize=(10,10),dpi=300)
        venn2(subsets = (dmisses, amisses,dhits), set_labels = ('Pseudotype Rabies \n Control Brain Regions', 'Allen Brain Atlas: \n Mouse Connectivity \n Target Dataset (ACC, PL, IL) '))
        plt.savefig(filename)

    def individual_subjects(self):
        self.data["uid"] = self.data["cage"] + self.data["subjectid"]
        for uid in pd.unique(self.data["uid"]):
            doh = self.data.loc[self.data['uid'] == uid]
            dataregions=doh[f'lv7']
            allenregions=self.allen['structure-name']
            dataregions=dataregions.to_numpy()
            allenregions=allenregions.to_numpy()
            dataregions=np.unique(dataregions)
            allenregions=np.unique(allenregions)
            dhits,dmisses,ahits,amisses=self.get_stats(dataregions,allenregions)
            percent_overlap=dhits/(dhits+dmisses+amisses)
            print(f'This is the percent intersection of data: {percent_overlap}')
            self.vendiagram(dmisses,amisses,dhits,f'subject{uid}.pdf')

if __name__=='__main__':
    ob=get_brain_regions(r'C:\Users\listo\rabies_cort_cohort2_dataset.csv',r'C:\rabiessummarydata_test\projection_search_results_isocortex.csv')
    ob.tresh_analysis()
    ob.plot_IOU_results()
    print(ob.maxiou)
    #ob.get_regions()
    #ob.individual_subjects()

