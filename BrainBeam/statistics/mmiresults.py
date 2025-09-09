import os
import re
import numpy as np
import pandas as pd
import ipdb

def parse_logs(root_dir):
    results = []
    
    # Updated regex patterns
    prior_pattern = re.compile(
        r"The\s+MMI\s+prior\s+to\s+nonrigid\s+alignment\s+is\s+([-+]?\d*\.\d+|\d+)",
        re.IGNORECASE
    )
    final_pattern = re.compile(
        r"Final\s+MMI\s+value:\s+([-+]?\d*\.\d+|\d+)",
        re.IGNORECASE
    )
    
    # Walk through directory and subdirectories
    for dirpath, _, filenames in os.walk(root_dir):
        for file in filenames:
            if file.lower().endswith(".log"):
                log_path = os.path.join(dirpath, file)
                first_prior = None
                last_final = None
                
                with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        prior_match = prior_pattern.search(line)
                        if prior_match and first_prior is None:
                            first_prior = float(prior_match.group(1))
                        
                        final_match = final_pattern.search(line)
                        if final_match:
                            last_final = float(final_match.group(1))
                
                if first_prior is not None and last_final is not None:
                    results.append([first_prior, last_final])
    
    # Convert to NumPy array
    return np.array(results)

if __name__ == "__main__":
    directory = r"C:\Users\listo\communal_registration_logcal_drop"
    data_array = parse_logs(directory)
    results = np.array(data_array)
    df = pd.DataFrame(results, columns=["pre", "post"])
    df.index.name = "suid"
    df.to_csv(os.path.join(directory,'MMI_nonrigid_results.csv'))
