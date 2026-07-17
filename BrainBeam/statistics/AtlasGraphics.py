#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: AtlasGraphics.py
Description: 
Author: David Estrin
Date: 2025-07-21
Version: 3.0
"""
import os
import json
import nrrd
import numpy as np
import pandas as pd
from tqdm import tqdm
from collections import defaultdict
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn, TimeRemainingColumn
from concurrent.futures import ThreadPoolExecutor, as_completed
import matplotlib as mpl
mpl.use("Agg") 
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib import cm
from matplotlib.patches import Circle
from scipy.ndimage import gaussian_filter
from scipy.stats import sem
from scipy.ndimage import distance_transform_edt, binary_erosion
import statsmodels.api as sm
from BrainBeam.registration.atlastree import atlastree
import ipdb
from matplotlib.patches import RegularPolygon
from matplotlib.patches import Polygon


class AtlasGraph:
    def __init__(self, dataframe, atlas_path, drop_directory,filename='tslices_nothreshold_updated.jpg',
                 default_decrease_color = np.array([224, 76, 92]) , default_increase_color = np.array([0, 148, 209]) ):
        self.atlas_path = atlas_path
        self.df = dataframe
        self.drop_directory = drop_directory
        self.df = self.df.dropna(axis=0)
        self.filename = filename
        self.abbreviated_filename = filename[:-4]

        self.default_decrease_color = default_decrease_color/255
        self.default_increase_color = default_increase_color/255

    def __call__(self):
        self.get_tree_obj()
        self.get_blank_atlas()
        self.get_ids()
        self.fill_atlas(threshold=0, filename=self.filename)
        self.fill_atlas(threshold=2.13, filename=f'{self.filename[:-4]}_thresholded_tslices.jpg')
        self.fill_atlas(stat='neg_log_p_value', threshold=1.3010299, filename= f'{self.filename[:-4]}_pslices.jpg')

        # Get gradient of t-values    
        self.plot_avg_tvalue_along_axis(axis=0, stat='t_value', filename_prefix=f'{self.abbreviated_filename}_Anterior_Posterior', bin_size=1) # Anterior → Posterior 
        self.plot_avg_tvalue_along_axis(axis=1, stat='t_value', filename_prefix=f'{self.abbreviated_filename}_Dorsal_Ventral', bin_size=1) # Dorsal → Ventral
        self.plot_avg_tvalue_along_axis(axis=2, stat='t_value', filename_prefix=f'{self.abbreviated_filename}_Left_Right', bin_size=1) # Ipsi → Contra
        self.plot_avg_tvalue_medial_to_lateral(stat='t_value', filename_prefix=f'{self.abbreviated_filename}_Medial_Lateral') # Medial → Lateral
        self.plot_avg_tvalue_cortical_to_basal(stat='t_value', filename_prefix=f'{self.abbreviated_filename}_Cortical_Basal', bin_size=1) # Cortical → Basal
        self.plot_avg_tvalue_distance_from_pfc( stat='t_value', filename_prefix=f'{self.abbreviated_filename}_Proximal_Distal', bin_size=1) #Proximal →  Distal

        self.distancedf,self.mpfcdistancedf = self.plot_centered_avg_tvalue_by_region_normalized() 
        self.distancedf.to_csv(os.path.join(self.drop_directory,f'{self.abbreviated_filename}_distancesdf.csv'))
        self.mpfcdistancedf.to_csv(os.path.join(self.drop_directory,f'{self.abbreviated_filename}_mpfc_distancesdf.csv'))
        
        self.plot_distance_profiles()
        self.plot_distance_profiles_norm()
        # self.fill_atlas_by_distance_from_pfc()

    def get_tree_obj(self):
        drop_atlas_path = os.path.join(self.atlas_path, "communal_atlas_drop/")
        atlas_json_file = os.path.join(drop_atlas_path, 'structures.json')
        with open(atlas_json_file, 'r') as infile:
            ontology_dict = json.load(infile)

        ontology_dict_oh = {i: v for i, v in enumerate(ontology_dict)}
        self.tree_obj = atlastree(data=ontology_dict_oh)

    def get_blank_atlas(self, annotation_path=None):
        if annotation_path is None:
            annotation_path = os.path.join(
                self.atlas_path,
                'communal_atlas_drop',
                'annotation',
                'ccf_2017',
                'annotation_50.nrrd'
            )
        self.atlas, header = nrrd.read(annotation_path)

    def get_ids(self):
        ids = []
        for name in self.df["regionname"]:
            try:
                ids.append(self.tree_obj.find_node(id_or_name=name)['id'])
            except Exception as exc:
                raise ValueError(f'Unable to resolve atlas region ID for "{name}"') from exc

        self.df.insert(0, 'id', ids)


    def fill_atlas(self, stat='t_value', threshold=1, filename='tslices.jpg'):
        t_min, t_max = self.df[stat].min(), self.df[stat].max()
        stat_range = t_max - t_min
        if stat_range == 0:
            self.df['norm'] = 0.5
        else:
            self.df['norm'] = (self.df[stat] - t_min) / stat_range

        # Create color maps
        color_map_ipsi = {}
        color_map_contra = {}

        red_rgb = self.default_increase_color
        blue_rgb = self.default_decrease_color
        grey_bg = np.array([0.8, 0.8, 0.8])
        
        custom_cmap = LinearSegmentedColormap.from_list("custom_red_blue", [blue_rgb, [0.8,0.8,0.8], red_rgb])

        for _, row in self.df.iterrows():
            if abs(row[stat]) >= threshold:
                if row['t_value'] < 0:
                    color = grey_bg * (1 - row['norm']) + blue_rgb * row['norm']  #  blue = decrease
                else:
                    color = grey_bg * (1 - row['norm']) + red_rgb * row['norm']   #  red = increase

                if row['lateralization'] == 'ipsilateral':
                    color_map_ipsi[row['id']] = color
                elif row['lateralization'] == 'contralateral':
                    color_map_contra[row['id']] = color

        colored_atlas = np.ones((*self.atlas.shape, 3))  # white by default
        midpoint = self.atlas.shape[2] // 2
        unique_ids = np.unique(self.atlas)
        for region_id in unique_ids:
            mask = self.atlas == region_id
            if region_id in self.df['id'].values:
                if region_id in color_map_ipsi:
                    color_left = color_map_ipsi[region_id]
                else:
                    grey_val = 0.5 + 0.2 * (region_id % 5) / 5
                    color_left = [grey_val, grey_val, grey_val]

                if region_id in color_map_contra:
                    color_right = color_map_contra[region_id]
                else:
                    grey_val = 0.5 + 0.2 * (region_id % 5) / 5
                    color_right = [grey_val, grey_val, grey_val]
            else:
                color_left = color_right = [1, 1, 1]

            left_mask = np.copy(mask)
            left_mask[:, :, midpoint:] = False
            right_mask = np.copy(mask)
            right_mask[:, :, :midpoint] = False

            colored_atlas[left_mask] = color_left
            colored_atlas[right_mask] = color_right

        slice_indices = [29, 58, 87, 116, 145, 174, 203, 232, 255]

        # Plot the colored atlas slices as before...
        fig, axes = plt.subplots(3, 3, figsize=(20, 20))
        for ax, idx in zip(axes.flat, slice_indices):
            slice_img = colored_atlas[idx, :, :]
            ax.imshow(slice_img)
            ax.axis("off")

            unique_regions = np.unique(self.atlas[idx, :, :])
            unique_regions = unique_regions[unique_regions != 0]

            for region_id in unique_regions:
                region_mask = (self.atlas[idx, :, :] == region_id).astype(float)
                smoothed_mask = gaussian_filter(region_mask, sigma=0.8)
                ax.contour(smoothed_mask, levels=[0.5], colors='k', linewidths=1.7)

        norm = mpl.colors.Normalize(vmin=t_min, vmax=t_max)
        sm = mpl.cm.ScalarMappable(cmap=custom_cmap, norm=norm)
        sm.set_array([])
        cbar_ax = fig.add_axes([0.92, 0.15, 0.02, 0.7])
        fig.colorbar(sm, cax=cbar_ax)

        plt.tight_layout(rect=[0, 0, 0.9, 1])
        plt.savefig(os.path.join(self.drop_directory, filename), dpi=300)
        plt.close(fig)


    def plot_avg_tvalue_along_axis(self, axis=0, stat='t_value', filename_prefix='binned_avg_tvalue', bin_size=1):
        """
        Bins slices of the atlas along a given axis, computes weighted average ± SEM of `stat` per bin,
        and generates a plot + CSV.

        axis:
            0 = Anterior → Posterior
            1 = Dorsal → Ventral
            2 = Left (Ipsi) → Right (Contra)
        """
        num_slices = self.atlas.shape[axis]
        slice_bins = list(range(0, num_slices, bin_size))

        bin_means = []
        bin_sems = []
        bin_labels = []

        for start in slice_bins:
            end = min(start + bin_size, num_slices)
            combined_region_values = {}
            combined_region_sizes = {}

            # iterate along chosen axis
            slicer = [slice(None)] * 3  # placeholder for :,:,
            for s in range(start, end):
                slicer[axis] = s
                slice_data = self.atlas[tuple(slicer)]
                regions, counts = np.unique(slice_data, return_counts=True)

                for region, count in zip(regions, counts):
                    if region == 0:
                        continue  # skip background

                    row = self.df[self.df['id'] == region]
                    if not row.empty:
                        tval = row[stat].values[0]

                        if region not in combined_region_values:
                            combined_region_values[region] = 0
                            combined_region_sizes[region] = 0

                        combined_region_values[region] += tval * count
                        combined_region_sizes[region] += count

            # Weighted average per bin
            values = []
            weights = []
            for region in combined_region_values:
                w = combined_region_sizes[region]
                if w == 0:
                    continue
                avg_tval = combined_region_values[region] / w
                values.append(avg_tval)
                weights.append(w)

            if not weights:
                bin_means.append(np.nan)
                bin_sems.append(np.nan)
            else:
                values = np.array(values)
                weights = np.array(weights)

                mean = np.average(values, weights=weights)
                variance = np.average((values - mean) ** 2, weights=weights)
                sem_val = np.sqrt(variance) / np.sqrt(len(values))

                bin_means.append(mean)
                bin_sems.append(sem_val)

            bin_labels.append(f"{start}-{end-1}")

        # Plotting
        plt.figure(figsize=(10, 6))
        x_ticks = np.arange(len(bin_labels))
        plt.errorbar(x_ticks, bin_means, yerr=bin_sems, fmt='-o', color='blue',
                    ecolor='lightblue', capsize=4)
        plt.xticks(x_ticks, bin_labels, rotation=45)

        axis_names = {0: 'Anterior→Posterior', 1: 'Dorsal→Ventral', 2: 'Ipsi→Contra'}
        plt.xlabel(f'{axis_names.get(axis, "Axis " + str(axis))} bins (every {bin_size} slices)')
        plt.ylabel(f'Weighted Average {stat}')
        plt.title(f'Weighted Avg {stat} ± SEM per {bin_size}-slice bin ({axis_names.get(axis, "Axis")})')
        plt.grid(True)
        plt.tight_layout()

        filename = os.path.join(self.drop_directory, f'{filename_prefix}_axis{axis}_bin{bin_size}.jpg')
        plt.savefig(filename, dpi=300)
        plt.close()

        # Save CSV
        export_df = pd.DataFrame({
            'distance_bin': x_ticks,
            f'{stat}_mean': bin_means,
            f'{stat}_sem': bin_sems
        })
        csv_filename = os.path.join(self.drop_directory, f'{filename_prefix}_axis{axis}_bin{bin_size}.csv')
        export_df.to_csv(csv_filename, index=False)

    def plot_avg_tvalue_cortical_to_basal(self, stat='t_value', filename_prefix='binned_avg_tvalue_cortical_basal', bin_size=1):
        """
        Computes weighted average ± SEM of `stat` from cortical surface inward to basal regions
        based on voxel distance from the brain perimeter.
        """
        # Step 1: Make a mask of the brain (non-background)
        brain_mask = self.atlas > 0

        # Step 2: Find the brain perimeter (outer shell)
        eroded = binary_erosion(brain_mask)
        perimeter_mask = brain_mask & ~eroded

        # Step 3: Distance transform inward from perimeter
        # For all brain voxels, how far they are from perimeter in voxels
        distance_map = distance_transform_edt(~perimeter_mask)  # distance from perimeter voxels

        # Step 4: Bin distances and compute weighted averages
        max_dist = int(distance_map[brain_mask].max())
        bin_edges = np.arange(0, max_dist + bin_size, bin_size)

        bin_means = []
        bin_sems = []
        bin_labels = []

        for start in bin_edges[:-1]:
            end = start + bin_size

            # Mask voxels in this bin
            bin_mask = (distance_map >= start) & (distance_map < end) & brain_mask

            # Extract regions and voxel counts
            regions, counts = np.unique(self.atlas[bin_mask], return_counts=True)

            combined_region_values = {}
            combined_region_sizes = {}

            for region, count in zip(regions, counts):
                if region == 0:
                    continue
                row = self.df[self.df['id'] == region]
                if not row.empty:
                    tval = row[stat].values[0]
                    if region not in combined_region_values:
                        combined_region_values[region] = 0
                        combined_region_sizes[region] = 0
                    combined_region_values[region] += tval * count
                    combined_region_sizes[region] += count

            values = []
            weights = []
            for region in combined_region_values:
                w = combined_region_sizes[region]
                if w > 0:
                    avg_tval = combined_region_values[region] / w
                    values.append(avg_tval)
                    weights.append(w)

            if weights:
                values = np.array(values)
                weights = np.array(weights)
                mean = np.average(values, weights=weights)
                variance = np.average((values - mean) ** 2, weights=weights)
                sem_val = np.sqrt(variance) / np.sqrt(len(values))
            else:
                mean = np.nan
                sem_val = np.nan

            bin_means.append(mean)
            bin_sems.append(sem_val)
            bin_labels.append(f"{start}-{end-1}")

        # Step 5: Plot
        plt.figure(figsize=(10, 6))
        x_ticks = np.arange(len(bin_labels))
        plt.errorbar(x_ticks, bin_means, yerr=bin_sems, fmt='-o', color='blue',
                    ecolor='lightblue', capsize=4)
        plt.xticks(x_ticks, bin_labels, rotation=45)
        plt.xlabel(f'Distance from Cortical Surface (voxels, bin={bin_size})')
        plt.ylabel(f'Weighted Average {stat}')
        plt.title(f'Cortical→Basal Weighted Avg {stat} ± SEM')
        plt.grid(True)
        plt.tight_layout()

        filename = os.path.join(self.drop_directory, f'{filename_prefix}_bin{bin_size}.jpg')
        plt.savefig(filename, dpi=300)
        plt.close()

        # Step 6: Save CSV
        export_df = pd.DataFrame({
            'distance_bin': bin_labels,
            f'{stat}_mean': bin_means,
            f'{stat}_sem': bin_sems
        })
        csv_filename = os.path.join(self.drop_directory, f'{filename_prefix}_bin{bin_size}.csv')
        export_df.to_csv(csv_filename, index=False)


    def plot_avg_tvalue_medial_to_lateral(self, stat='t_value', filename_prefix='avg_tvalue_medlat'):
        num_cols = self.atlas.shape[2]
        midline = num_cols // 2
        max_medial_distance = midline  # assumes symmetry

        distances = []
        avg_tvals = []
        bin_sems = []

        for m in range(max_medial_distance):
            combined_region_values = {}
            combined_region_sizes = {}

            for s in range(self.atlas.shape[0]):  # loop over slices
                slice_data = self.atlas[s, :, :]

                for side in [-1, 1]:  # left (-1) and right (+1)
                    col = midline + side * m
                    if col < 0 or col >= num_cols:
                        continue

                    column_data = slice_data[:, col]
                    regions, counts = np.unique(column_data, return_counts=True)

                    for region, count in zip(regions, counts):
                        if region == 0:
                            continue  # skip background

                        if region not in combined_region_sizes:
                            combined_region_sizes[region] = 0
                            combined_region_values[region] = 0

                        row = self.df[self.df['id'] == region]
                        if not row.empty:
                            tval = row[stat].values[0]
                            combined_region_sizes[region] += count
                            combined_region_values[region] += tval * count

            total_weights = sum(combined_region_sizes.values())
            if total_weights == 0:
                avg_tvals.append(np.nan)
                bin_sems.append(np.nan)
            else:
                valid_regions = [r for r in combined_region_sizes if combined_region_sizes[r] != 0]
                weighted_tvals = np.array([
                    combined_region_values[r] / combined_region_sizes[r]
                    for r in valid_regions
                ])
                weights = np.array([combined_region_sizes[r] for r in valid_regions])

                mean = np.average(weighted_tvals, weights=weights)
                variance = np.average((weighted_tvals - mean) ** 2, weights=weights)
                sem_val = np.sqrt(variance) / np.sqrt(len(weighted_tvals))

                avg_tvals.append(mean)
                bin_sems.append(sem_val)

            distances.append(m)

        # Plotting
        plt.figure(figsize=(10, 6))
        plt.plot(distances, avg_tvals, '-o', color='purple')
        plt.xlabel('Distance from Midline (pixels)')
        plt.ylabel(f'Weighted Average {stat}')
        plt.title(f'Weighted Average {stat} by Distance from Midline')
        plt.grid(True)
        plt.tight_layout()

        export_df = pd.DataFrame({
            'distance_bin': distances,
            f'{stat}_mean': avg_tvals,
            f'{stat}_sem': bin_sems
        })

        # Save CSV
        csv_filename = os.path.join(self.drop_directory, f'{filename_prefix}_bin{0}.csv')
        export_df.to_csv(csv_filename, index=False)

        filename = os.path.join(self.drop_directory, f'{filename_prefix}.jpg')
        plt.savefig(filename, dpi=300)
        plt.close()

    def plot_avg_tvalue_distance_from_amygdala(self, stat='t_value', filename_prefix='avg_tvalue_from_amygdala', bin_size=1):
        # Define amygdala region names (match substring and ensure ipsilateral only)
        amygdala_mask = self.df['regionname'].str.lower().str.contains('amygda') & self.df['lateralization'].str.lower().str.contains('ipsi')
        amygdala_ids = self.df[amygdala_mask]['id'].values

        # Get all voxel coordinates belonging to ipsilateral amygdala
        amygdala_coords = np.argwhere(np.isin(self.atlas, amygdala_ids))
        if amygdala_coords.size == 0:
            raise ValueError("No ipsilateral amygdala voxels found in atlas.")

        # Compute center of mass of the ipsilateral amygdala
        center = amygdala_coords.mean(axis=0)

        # Map region ID → t-value
        region_to_tval = dict(zip(self.df['id'].values, self.df[stat].values))

        shape = self.atlas.shape
        tvals_list = []
        distances_list = []

        for idx in tqdm(np.ndindex(shape), total=np.prod(shape), desc="Processing voxels"):
            region = self.atlas[idx]
            if region == 0:
                continue
            tval = region_to_tval.get(region)
            if tval is None:
                continue
            dist = np.linalg.norm(np.array(idx) - center)
            tvals_list.append(tval)
            distances_list.append(dist)

        # Average distance per unique t-value
        unique_tvals = {}
        counts = {}
        for tval, dist in zip(tvals_list, distances_list):
            unique_tvals[tval] = unique_tvals.get(tval, 0) + dist
            counts[tval] = counts.get(tval, 0) + 1
        avg_distances_per_tval = {t: unique_tvals[t]/counts[t] for t in unique_tvals}

        # OLS regression
        tvals_unique = np.array(list(avg_distances_per_tval.keys()))
        distances_unique = np.array([avg_distances_per_tval[t] for t in tvals_unique])
        X = sm.add_constant(distances_unique)
        model = sm.OLS(tvals_unique, X).fit()
        print(f"Regression F-value: {model.fvalue:.4f}, p-value: {model.f_pvalue:.4e}")

        # Bin and plot
        from collections import defaultdict
        from scipy.stats import sem

        binned_tvals = defaultdict(list)
        for tval, dist in zip(tvals_list, distances_list):
            bin_idx = (int(dist) // bin_size) * bin_size
            binned_tvals[bin_idx].append(tval)

        bins = sorted(binned_tvals.keys())
        means = [np.mean(binned_tvals[b]) for b in bins]
        sems = [sem(binned_tvals[b]) if len(binned_tvals[b]) > 1 else 0 for b in bins]

        plt.figure(figsize=(10, 6))
        plt.errorbar(bins, means, yerr=sems, fmt='-o', color='purple', ecolor='orchid', capsize=4)
        plt.xlabel(f'Distance from Amygdala center (binned every {bin_size} voxels)')
        plt.ylabel(f'Average {stat}')
        plt.title(f'{stat} as a Function of Distance from Amygdala (Binned)')
        plt.grid(True)
        plt.tight_layout()

        filename = os.path.join(self.drop_directory, f'{filename_prefix}_bin{bin_size}.jpg')
        plt.savefig(filename, dpi=300)
        plt.close()

        export_df = pd.DataFrame({
            'distance_bin': bins,
            f'{stat}_mean': means,
            f'{stat}_sem': sems
        })
        csv_filename = os.path.join(self.drop_directory, f'{filename_prefix}_bin{bin_size}.csv')
        export_df.to_csv(csv_filename, index=False)

    def plot_avg_tvalue_distance_from_pfc(self, stat='t_value', filename_prefix='avg_tvalue_from_pfc', bin_size=1):
        # Define PFC region names
        pfc_regions = ['prelimbic', 'infralimbic', 'anterior cingulate']
        pfc_ids = self.df[self.df['regionname'].str.lower().apply(
            lambda name: any(pfc in name for pfc in pfc_regions))]['id'].values

        # Get all voxel coordinates that belong to PFC
        pfc_coords = np.argwhere(np.isin(self.atlas, pfc_ids))
        if pfc_coords.size == 0:
            raise ValueError("No PFC voxels found in atlas.")

        # Compute center of PFC
        center = pfc_coords.mean(axis=0)

        # Create a lookup dictionary: region ID → t-value
        region_to_tval = dict(zip(self.df['id'].values, self.df[stat].values))

        shape = self.atlas.shape

        # Collect voxels' t-values and distances
        tvals_list = []
        distances_list = []

        for idx in tqdm(np.ndindex(shape), total=np.prod(shape), desc="Processing voxels"):
            region = self.atlas[idx]
            if region == 0:
                continue  # Skip background

            tval = region_to_tval.get(region)
            if tval is None:
                continue  # Region not in dataframe

            dist = np.linalg.norm(np.array(idx) - center)

            tvals_list.append(tval)
            distances_list.append(dist)

        # Group by unique t-values: calculate mean distance for each unique t-value
        unique_tvals = {}
        counts = {}

        for tval, dist in zip(tvals_list, distances_list):
            if tval not in unique_tvals:
                unique_tvals[tval] = dist
                counts[tval] = 1
            else:
                unique_tvals[tval] += dist
                counts[tval] += 1

        avg_distances_per_tval = {t: unique_tvals[t]/counts[t] for t in unique_tvals}

        # Prepare data for regression: unique t-values and their avg distances
        tvals_unique = np.array(list(avg_distances_per_tval.keys()))
        distances_unique = np.array([avg_distances_per_tval[t] for t in tvals_unique])

        # Run OLS regression: tval ~ avg_distance
        X = sm.add_constant(distances_unique)
        model = sm.OLS(tvals_unique, X).fit()

        print(f"Regression F-value: {model.fvalue:.4f}, p-value: {model.f_pvalue:.4e}")

        # Now also plot binned average t-values as before (using all voxels)
        binned_tvals = defaultdict(list)
        for tval, dist in zip(tvals_list, distances_list):
            bin_idx = (int(dist) // bin_size) * bin_size
            binned_tvals[bin_idx].append(tval)

        bins = sorted(binned_tvals.keys())
        means = [np.mean(binned_tvals[b]) for b in bins]
        sems = [sem(binned_tvals[b]) if len(binned_tvals[b]) > 1 else 0 for b in bins]

        plt.figure(figsize=(10, 6))
        plt.errorbar(bins, means, yerr=sems, fmt='-o', color='green', ecolor='lightgreen', capsize=4)
        plt.xlabel(f'Distance from PFC center (binned every {bin_size} voxels)')
        plt.ylabel(f'Average {stat}')
        plt.title(f'{stat} as a Function of Distance from PFC (Binned)')
        plt.grid(True)
        plt.tight_layout()

        filename = os.path.join(self.drop_directory, f'{filename_prefix}_bin{bin_size}.jpg')
        plt.savefig(filename, dpi=300)
        plt.close()

        export_df = pd.DataFrame({
            'distance_bin': bins,
            f'{stat}_mean': means,
            f'{stat}_sem': sems
        })

        # Save CSV
        csv_filename = os.path.join(self.drop_directory, f'{filename_prefix}_bin{bin_size}.csv')
        export_df.to_csv(csv_filename, index=False)

    def plot_centered_avg_tvalue_by_region_normalized(
        self, stat='t_value', filename_prefix='centered_avg_tval_norm',
        min_voxels_per_side=10, n_bins=100, n_threads=8):
        """
        For each non-mPFC region, compute a line: normalized distance (0–1) vs average t-value.
        Also returns a dataframe for mPFC with mean ± SEM.
        """

        # Map region id → t-value
        region_to_tval = dict(zip(self.df['id'], self.df[stat].values))
        region_names = dict(zip(self.df['id'], self.df['regionname']))

        # Identify PFC
        pfc_regions = ['prelimbic', 'infralimbic', 'anterior cingulate']
        is_pfc = self.df['regionname'].str.lower().apply(
            lambda name: any(pfc in name for pfc in pfc_regions)
        )
        pfc_ids = self.df[is_pfc]['id'].values
        non_pfc_ids = self.df[~is_pfc]['id'].unique()

        # Global PFC center
        pfc_coords = np.argwhere(np.isin(self.atlas, pfc_ids))
        if pfc_coords.size == 0:
            raise ValueError("No PFC voxels found in atlas.")
        global_pfc_center = pfc_coords.mean(axis=0)

        shape = self.atlas.shape
        midline = shape[2] // 2

        # Precompute valid voxels and t-values
        all_coords = np.array(np.nonzero(self.atlas)).T
        region_ids_all = self.atlas[tuple(all_coords.T)]
        mask_valid = np.isin(region_ids_all, list(region_to_tval.keys()))
        coords_valid = all_coords[mask_valid]
        region_ids_valid = region_ids_all[mask_valid]
        tvals_valid = np.array([region_to_tval[r] for r in region_ids_valid])

        lines = []

        # --- Non-mPFC processing ---
        def process_region(region_id):
            region_mask = self.atlas == region_id
            if region_mask.sum() == 0:
                return None

            coords = np.argwhere(region_mask)
            left = coords[coords[:, 2] < midline]
            right = coords[coords[:, 2] >= midline]

            voxel_groups = []
            if left.shape[0] > min_voxels_per_side and right.shape[0] > min_voxels_per_side:
                voxel_groups.append(coords.mean(axis=0))
            else:
                if left.shape[0] >= min_voxels_per_side:
                    voxel_groups.append(left.mean(axis=0))
                if right.shape[0] >= min_voxels_per_side:
                    voxel_groups.append(right.mean(axis=0))

            region_lines = []
            for center in voxel_groups:
                distances = np.linalg.norm(coords_valid - center, axis=1)
                tvals_region = tvals_valid

                max_dist = distances.max()
                if max_dist == 0:
                    continue

                bins = np.linspace(0, max_dist, n_bins + 1)
                digitized = np.digitize(distances, bins) - 1

                sum_tvals = np.bincount(digitized, weights=tvals_region, minlength=n_bins)
                count_tvals = np.bincount(digitized, minlength=n_bins)
                avg_tvals = sum_tvals / np.maximum(count_tvals, 1)
                avg_tvals[count_tvals == 0] = np.nan

                bin_centers = 0.5 * (bins[:-1] + bins[1:])
                normalized_dist = bin_centers / max_dist

                if len(avg_tvals) != len(normalized_dist):
                    min_len = min(len(avg_tvals), len(normalized_dist))
                    avg_tvals = avg_tvals[:min_len]
                    normalized_dist = normalized_dist[:min_len]

                df_line = pd.DataFrame({
                    "normalized_distance": normalized_dist,
                    "avg_tvalue": avg_tvals,
                    "regionname": [region_names[region_id]] * len(normalized_dist),
                    "region_type": ["non-mPFC"] * len(normalized_dist)
                })
                region_lines.append(df_line)

            if not region_lines:
                return None
            return pd.concat(region_lines, ignore_index=True)

        # --- Parallel processing with rich progress bar ---
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.1f}%",
            TimeElapsedColumn(),
            TimeRemainingColumn(),
        ) as progress:

            task = progress.add_task("Processing regions", total=len(non_pfc_ids))

            with ThreadPoolExecutor(max_workers=n_threads) as executor:
                futures = {executor.submit(process_region, rid): rid for rid in non_pfc_ids}
                for f in as_completed(futures):
                    result = f.result()
                    if result is not None:
                        lines.append(result)
                    progress.advance(task)

        df_lines = pd.concat(lines, ignore_index=True)

        # --- mPFC summary ---
        distances_mpfc = np.linalg.norm(coords_valid - global_pfc_center, axis=1)
        max_dist = distances_mpfc.max()
        bins = np.linspace(0, max_dist, n_bins + 1)
        digitized = np.digitize(distances_mpfc, bins) - 1

        sum_tvals = np.bincount(digitized, weights=tvals_valid, minlength=n_bins)
        count_tvals = np.bincount(digitized, minlength=n_bins)
        mean_tvals = sum_tvals / np.maximum(count_tvals, 1)
        mean_tvals[count_tvals == 0] = np.nan

        sem_tvals = np.array([
            np.nanstd(tvals_valid[digitized == i], ddof=1) / np.sqrt(np.sum(digitized == i)) 
            if np.any(digitized == i) else np.nan
            for i in range(n_bins)
        ])

        bin_centers = 0.5 * (bins[:-1] + bins[1:])
        normalized_dist = bin_centers / max_dist

        # Ensure lengths match
        min_len = min(len(mean_tvals), len(normalized_dist))
        df_mpfc = pd.DataFrame({
            "normalized_distance": normalized_dist[:min_len],
            "mean_tvalue": mean_tvals[:min_len],
            "sem_tvalue": sem_tvals[:min_len],
            "region_type": ["mPFC"] * min_len
        })

        return df_lines, df_mpfc

    def plot_distance_profiles(self, ax=None):
        """
        Plot mean ± SEM of mPFC vs non-mPFC, and overlay individual non-mPFC regions with alpha=0.1.
        Non-mPFC data comes from self.distancedf, mPFC data from self.mpfcdistancedf.
        """

        if self.distancedf is None or self.distancedf.empty:
            raise ValueError("self.distancedf is empty. Run the non-mPFC distance calculation first.")
        if self.mpfcdistancedf is None or self.mpfcdistancedf.empty:
            raise ValueError("self.mpfcdistancedf is empty. Run the mPFC distance calculation first.")

        nonPFC_df = self.distancedf
        mPFC_df = self.mpfcdistancedf

        if ax is None:
            fig, ax = plt.subplots(figsize=(8, 6))

        # --- Plot individual non-mPFC regions ---
        for region, group in nonPFC_df.groupby('regionname'):
            ax.plot(group['normalized_distance'], group['avg_tvalue'], color='blue', alpha=0.05)

        # --- Bin parameters ---
        bins = np.linspace(0, 1, 100)
        bin_centers = 0.5 * (bins[:-1] + bins[1:])

        def aggregate(df_subset, value_col='avg_tvalue'):
            avg_vals = []
            sem_vals = []
            for i in range(len(bins) - 1):
                mask = (df_subset['normalized_distance'] >= bins[i]) & (df_subset['normalized_distance'] < bins[i + 1])
                y = df_subset.loc[mask, value_col]
                avg_vals.append(y.mean() if not y.empty else np.nan)
                sem_vals.append(sem(y, nan_policy='omit') if not y.empty else np.nan)
            return np.array(avg_vals), np.array(sem_vals)

        # --- Non-mPFC mean ± SEM ---
        non_mean, non_sem = aggregate(nonPFC_df)
        ax.fill_between(bin_centers, non_mean - non_sem, non_mean + non_sem, color='blue', alpha=0.3)
        ax.plot(bin_centers, non_mean, color='blue', label='non-mPFC mean ± SEM', linewidth=2)

        # --- mPFC mean ± SEM ---
        mpfc_mean, mpfc_sem = aggregate(mPFC_df, value_col='mean_tvalue')
        ax.fill_between(bin_centers, mpfc_mean - mpfc_sem, mpfc_mean + mpfc_sem, color='gold', alpha=0.5)
        ax.plot(bin_centers, mpfc_mean, color='gold', label='mPFC mean ± SEM', linewidth=2)

        ax.set_xlabel("Normalized distance from region center")
        ax.set_ylabel("Average t-value")
        ax.legend()
        ax.set_title("Distance-dependent t-value profiles")
        ax.grid(True)
        plt.tight_layout()

        filename = os.path.join(self.drop_directory, f'{self.abbreviated_filename}_distance_tvals.jpg')
        plt.savefig(filename)

    def plot_distance_profiles_norm(self, ax=None):
        """
        Plot mean ± SEM of mPFC vs non-mPFC, and overlay individual non-mPFC regions with alpha=0.1.
        Non-mPFC data comes from self.distancedf, mPFC data from self.mpfcdistancedf.
        All values are shifted so that the first value of each region starts at zero.
        """

        if self.distancedf is None or self.distancedf.empty:
            raise ValueError("self.distancedf is empty. Run the non-mPFC distance calculation first.")
        if self.mpfcdistancedf is None or self.mpfcdistancedf.empty:
            raise ValueError("self.mpfcdistancedf is empty. Run the mPFC distance calculation first.")

        nonPFC_df = self.distancedf.copy()
        mPFC_df = self.mpfcdistancedf.copy()

        # --- Subtract first value per region to start at zero ---
        def normalize_start(df, value_col, group_col=None):
            df_norm = df.copy()
            if group_col is None:  # no grouping column, subtract first value of entire df
                first_val = df[value_col].iloc[0]
                df_norm[value_col] = df[value_col] - first_val
            else:  # group by a column (e.g., 'regionname')
                for region, group in df.groupby(group_col):
                    first_idx = group['normalized_distance'].idxmin()
                    first_val = group.loc[first_idx, value_col]
                    df_norm.loc[group.index, value_col] = group[value_col] - first_val
            return df_norm

        # Apply to nonPFC (grouped by region)
        nonPFC_df['avg_tvalue'] = normalize_start(nonPFC_df, 'avg_tvalue', group_col='regionname')['avg_tvalue']

        # Apply to mPFC (no regionname column)
        mPFC_df['mean_tvalue'] = normalize_start(mPFC_df, 'mean_tvalue')['mean_tvalue']

        if ax is None:
            fig, ax = plt.subplots(figsize=(8, 6))

        # --- Plot individual non-mPFC regions ---
        for region, group in nonPFC_df.groupby('regionname'):
            ax.plot(group['normalized_distance'], group['avg_tvalue'], color='blue', alpha=0.05)

        # --- Bin parameters ---
        bins = np.linspace(0, 1, 100)
        bin_centers = 0.5 * (bins[:-1] + bins[1:])

        def aggregate(df_subset, value_col='avg_tvalue'):
            avg_vals = []
            sem_vals = []
            for i in range(len(bins) - 1):
                mask = (df_subset['normalized_distance'] >= bins[i]) & (df_subset['normalized_distance'] < bins[i + 1])
                y = df_subset.loc[mask, value_col]
                avg_vals.append(y.mean() if not y.empty else np.nan)
                sem_vals.append(sem(y, nan_policy='omit') if not y.empty else np.nan)
            return np.array(avg_vals), np.array(sem_vals)

        # --- Non-mPFC mean ± SEM ---
        non_mean, non_sem = aggregate(nonPFC_df)
        ax.fill_between(bin_centers, non_mean - non_sem, non_mean + non_sem, color='blue', alpha=0.3)
        ax.plot(bin_centers, non_mean, color='blue', label='non-mPFC mean ± SEM', linewidth=2)

        # --- mPFC mean ± SEM ---
        mpfc_mean, mpfc_sem = aggregate(mPFC_df, value_col='mean_tvalue')
        ax.fill_between(bin_centers, mpfc_mean - mpfc_sem, mpfc_mean + mpfc_sem, color='gold', alpha=0.5)
        ax.plot(bin_centers, mpfc_mean, color='gold', label='mPFC mean ± SEM', linewidth=2)

        ax.set_xlabel("Normalized distance from region center")
        ax.set_ylabel("Average t-value (shifted to start at 0)")
        ax.legend()
        ax.set_title("Distance-dependent t-value profiles (zeroed at start)")
        ax.grid(True)
        plt.tight_layout()
        filename = os.path.join(self.drop_directory, f'{self.abbreviated_filename}_distance_tvals_norm.jpg')
        plt.savefig(filename)

    def fill_atlas_by_distance_from_pfc(self, bin_size=10, filename='distance_fill.jpg'):
        
        # Define PFC regions and get voxel indices
        pfc_regions = ['prelimbic', 'infralimbic', 'anterior cingulate']
        pfc_ids = self.df[self.df['regionname'].str.lower().apply(
            lambda name: any(pfc in name for pfc in pfc_regions))]['id'].values

        pfc_coords = np.argwhere(np.isin(self.atlas, pfc_ids))
        if pfc_coords.size == 0:
            raise ValueError("No PFC voxels found in atlas.")
        
        center = pfc_coords.mean(axis=0)

        # Get all valid voxels with data
        region_to_tval = dict(zip(self.df['id'].values, self.df['t_value'].values))

        # Compute distance for each voxel and bin them
        distance_map = np.full(self.atlas.shape, -1)  # initialize with -1 (invalid)
        all_distances = []

        shape = self.atlas.shape
        for idx in tqdm(np.ndindex(shape), total=np.prod(shape), desc="Computing distances"):
            region = self.atlas[idx]
            if region == 0 or region not in region_to_tval:
                continue

            dist = int(round(np.linalg.norm(np.array(idx) - center)))
            bin_dist = (dist // bin_size) * bin_size
            distance_map[idx] = bin_dist
            all_distances.append(bin_dist)

        if not all_distances:
            raise ValueError("No distances were computed. Check atlas and region IDs.")

        # Normalize binned distances to colormap
        unique_bins = sorted(set(all_distances))
        bin_to_norm = {b: i / (len(unique_bins) - 1) for i, b in enumerate(unique_bins)}
        cmap = cm.Greens_r  # Reversed Blues: dark to light

        # Create color atlas
        color_atlas = np.ones((*self.atlas.shape, 3))  # default white
        for idx in np.ndindex(self.atlas.shape):
            binned_dist = distance_map[idx]
            if binned_dist == -1:
                continue
            color = cmap(bin_to_norm[binned_dist])[:3]
            color_atlas[idx] = color

        # Plot slices (ensure center slice is included)
        z_center = int(round(center[0]))
        slice_indices = sorted(set([29, 58, 87, 116, 145, 174, 203, 232, 255, z_center]))[:9]

        fig, axes = plt.subplots(3, 3, figsize=(20, 20))
        for ax, idx in zip(axes.flat, slice_indices):
            slice_img = color_atlas[idx, :, :]
            ax.imshow(slice_img)
            ax.axis("off")

            # Draw region contours
            unique_regions = np.unique(self.atlas[idx, :, :])
            unique_regions = unique_regions[unique_regions != 0]
            for region_id in unique_regions:
                region_mask = (self.atlas[idx, :, :] == region_id).astype(float)
                smoothed_mask = gaussian_filter(region_mask, sigma=0.8)
                ax.contour(smoothed_mask, levels=[0.5], colors='k', linewidths=1.5, zorder=5)

            # If this is the center slice, add red circle
            if idx == z_center:
                y, x = center[1], center[2]
                circ = Circle((x, y), radius=6, color='#D95F02', fill=True, alpha=0.8, zorder=10)
                ax.add_patch(circ)

        # Colorbar
        norm = mpl.colors.Normalize(vmin=min(unique_bins), vmax=max(unique_bins))
        sm = mpl.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar_ax = fig.add_axes([0.92, 0.15, 0.02, 0.7])
        fig.colorbar(sm, cax=cbar_ax, label=f'Distance from PFC center (binned every {bin_size} voxels)')

        plt.tight_layout(rect=[0, 0, 0.9, 1])
        plt.savefig(os.path.join(self.drop_directory, filename), dpi=300)
        plt.close(fig)







