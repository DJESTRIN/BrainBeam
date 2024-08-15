from mass_ttest import mass_ttest, create_timestamped_directory
from scipy.stats import mannwhitneyu
import os

class mass_whitneytest(mass_ttest):
    def ttest(self, group1, group2):
        """ Run non-parametric mann whitney test instead """
        return mannwhitneyu(group1, group2)

if __name__=='__main__':
    # Run mass univariate t-tests
    filename_massttest = r'C:\Users\listo\level_analysis\bootstrap\datasets\mass_ttests_obj_boot.pkl'
    if os.path.isfile(filename_massttest):
        massttest_obj=mass_ttest.load(filename_massttest)
    else:
        output = create_timestamped_directory(r'C:\Users\listo\level_analysis\bootstrap\results')
        massttest_obj=mass_ttest(atlas_json_file = r'C:\Users\listo\BRAINBEAM\BRAINBEAM\statistics\datasets\ara_ontology.json',
                        atlas_path=r'C:\Users\listo\BRAINBEAM\BRAINBEAM\statistics\datasets\ara_annotation_10um.tif',
                        drop_directory=output,
                        dataframe_path=r'C:\Users\listo\level_analysis\datasets\rabies_cort_cohort2_dataset.csv')
        
        # Threshold T-values for dataframe
        #massttest_obj.drop_tvals=True
        #massttest_obj.drop_threshold=2
        massttest_obj.bootstrap=True

        #Run object pipeline
        massttest_obj()
        massttest_obj.save(filename_massttest)