#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: datagenerator.py
Description: 
Author: David Estrin
Date: 2024-12-11
Version: 1.0
"""
import pandas as pd
import numpy as np
import ipdb

def generate_pseudo_data(num_subjects=20,num_cages=5,groups=["CONTROL","CORT"],lambdaval=1):
    """ Note!!!
    This is for generating data simply for testing statistical code. This is not real data and should not be used as such.
    """
    # Parameters
    num_subjects = num_subjects
    cage_numbers = [f"C{str(i).zfill(2)}" for i in range(1, num_cages)]  # C01 to C20

    mouse_brain_regions = [
        "Hippocampus (CA1)", "Hippocampus (CA2)", "Hippocampus (CA3)", "Dentate Gyrus",
        "Prefrontal Cortex (dorsal)", "Prefrontal Cortex (ventral)", "Cerebellum (Vermis)", "Cerebellum (Hemispheres)",
        "Thalamus (Lateral)", "Thalamus (Medial)", "Amygdala (Basolateral)", "Amygdala (Central)", "Amygdala (Medial)",
        "Basal Ganglia (Caudate)", "Basal Ganglia (Putamen)", "Olfactory Bulb (Main)", "Olfactory Bulb (Accessory)",
        "Hypothalamus (Anterior)", "Hypothalamus (Posterior)", "Cerebral Cortex (Motor)", "Cerebral Cortex (Somatosensory)",
        "Cerebral Cortex (Visual)", "Cerebral Cortex (Auditory)", "Striatum (Dorsal)", "Striatum (Ventral)",
        "Medulla Oblongata (Dorsal)", "Medulla Oblongata (Ventral)", "Pons (Dorsal)", "Pons (Ventral)",
        "Midbrain (Tectum)", "Midbrain (Tegmentum)", "Occipital Lobe (Primary Visual Cortex)",
        "Parietal Lobe (Somatosensory Cortex)", "Temporal Lobe (Auditory Cortex)", "Frontal Lobe (Precentral Gyrus)",
        "Spinal Cord (Cervical)", "Spinal Cord (Thoracic)", "Spinal Cord (Lumbar)", "Entorhinal Cortex (Lateral)",
        "Entorhinal Cortex (Medial)", "Nucleus Accumbens (Core)", "Nucleus Accumbens (Shell)", 
        "Substantia Nigra (Pars Compacta)", "Substantia Nigra (Pars Reticulata)", "Ventral Tegmental Area (Medial)",
        "Septum (Lateral)", "Septum (Medial)", "Dorsal Raphe Nucleus (Lateral)", "Dorsal Raphe Nucleus (Medial)",
        "Locus Coeruleus (Rostral)", "Locus Coeruleus (Caudal)", "Superior Colliculus (Superficial)", 
        "Superior Colliculus (Deep)", "Inferior Colliculus (Central)", "Inferior Colliculus (Pericentral)",
        "Lateral Geniculate Nucleus (Dorsal)", "Lateral Geniculate Nucleus (Ventral)",
        "Medial Geniculate Nucleus (Dorsal)", "Medial Geniculate Nucleus (Ventral)",
        "Periaqueductal Gray (Dorsal)", "Periaqueductal Gray (Lateral)", "Cingulate Cortex (Anterior)", 
        "Cingulate Cortex (Posterior)", "Insular Cortex (Anterior)", "Insular Cortex (Posterior)", 
        "Piriform Cortex (Anterior)", "Piriform Cortex (Posterior)", "Anterior Commissure (Anterior)", 
        "Anterior Commissure (Posterior)", "Fornix (Column)", "Fornix (Body)", "Corpus Callosum (Genu)", 
        "Corpus Callosum (Splenium)", "Internal Capsule (Anterior Limb)", "Internal Capsule (Posterior Limb)", 
        "Claustrum (Anterior)", "Claustrum (Posterior)", "Globus Pallidus (External)", "Globus Pallidus (Internal)", 
        "Subthalamic Nucleus (Anterior)", "Subthalamic Nucleus (Posterior)", "Red Nucleus (Parvocellular)", 
        "Red Nucleus (Magnocellular)", "Bed Nucleus of the Stria Terminalis (Anterior)", 
        "Bed Nucleus of the Stria Terminalis (Posterior)", "Subiculum (Proximal)", "Subiculum (Distal)", 
        "Zona Incerta (Anterior)", "Zona Incerta (Posterior)", "Reticular Formation (Rostral)", 
        "Reticular Formation (Caudal)", "Paraventricular Nucleus (Magnocellular)", 
        "Paraventricular Nucleus (Parvocellular)", "Suprachiasmatic Nucleus (Dorsal)", 
        "Suprachiasmatic Nucleus (Ventral)", "Mamillary Bodies (Medial)", "Mamillary Bodies (Lateral)", 
        "Lateral Hypothalamus (Anterior)", "Lateral Hypothalamus (Posterior)", "Dorsal Thalamus (Anterior)", 
        "Dorsal Thalamus (Posterior)", "Spinal Cord (Sacral)", "Insular Cortex (Granular)", "Insular Cortex (Dysgranular)", 
        "Anterior Commissure (Intermediate)", "Anterior Commissure (Caudal)", "Fornix (Crescent)", 
        "Corpus Callosum (Body)", "Internal Capsule (Retrolenticular)", "Internal Capsule (Sublenticular)",
        "Claustrum (Ventral)", "Claustrum (Dorsal)", "Globus Pallidus (Caudal)", "Globus Pallidus (Rostral)", 
        "Subthalamic Nucleus (Lateral)", "Subthalamic Nucleus (Medial)", "Red Nucleus (Lateral)", 
        "Red Nucleus (Medial)", "Bed Nucleus of the Stria Terminalis (Central)", "Bed Nucleus of the Stria Terminalis (Dorsal)", 
        "Subiculum (Ventral)", "Subiculum (Dorsal)", "Zona Incerta (Medial)", "Zona Incerta (Lateral)", 
        "Reticular Formation (Medial)", "Reticular Formation (Lateral)", "Paraventricular Nucleus (Intermediate)", 
        "Paraventricular Nucleus (Posterior)", "Suprachiasmatic Nucleus (Lateral)", "Suprachiasmatic Nucleus (Medial)", 
        "Mamillary Bodies (Caudal)", "Mamillary Bodies (Rostral)", "Lateral Hypothalamus (Intermediate)", 
        "Lateral Hypothalamus (Caudal)", "Dorsal Thalamus (Lateral)", "Dorsal Thalamus (Medial)", "Insular Cortex (Intermediate)"
    ]

    # Generate data
    np.random.seed(0)  
    subject_ids = [f"S{str(i).zfill(3)}" for i in range(1, num_subjects + 1)]
    cage_number = np.random.choice(cage_numbers, num_subjects)
    group = np.random.choice(groups, num_subjects)

    expanded_data = []
    for i in range(num_subjects):
        for region in mouse_brain_regions:
            expanded_data.append({
                "SubjectID": subject_ids[i],
                "CageNumber": cage_number[i],
                "Group": group[i],
                "BrainRegion": region,
                "NumberOfCells":  np.random.poisson(lambdaval)
            })
    df = pd.DataFrame(expanded_data)
    return df

def increase_pseudo_stability(X, y, percent_data=0.4):
    # Randomly change a certain percent of the data to be equal
    for k,row in enumerate(X['CONTROL']):
        if np.random.random()<percent_data:
            X['CONTROL'][k] = y[k]
   
    return X, y