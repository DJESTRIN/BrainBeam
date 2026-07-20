# Human comparison supplement

This folder contains supplemental analyses meant to place the mouse mPFC circuit findings in cautious human translational context. They are **hypothesis-generating supplements**, not validation analyses of comparable evidentiary strength to the mouse anatomy-weighted GLMM circuit model, the calcium-imaging multivalence results, or the ketamine causal-reversal experiment.

1. `neurosynth_coactivation.py` builds parcel-level human **term-associated activation-density** summaries for fear/threat/stress-related Neurosynth terms using the small term-annotation release distributed through NiMARE plus the bundled Harvard-Oxford atlas from Nilearn.
2. `build_enigma_table.py` compiles a literature-only ENIGMA PTSD/MDD convergence table from published summary statistics.
3. `make_figures.py` turns the generated CSV outputs into reader-facing figure panels for the supplement, including atlas-backprojected Nilearn brain renderings.

## Why this exists

The eventual paper needs a cautious mouse-to-human bridge. These analyses do **not** claim one-to-one homology between mouse prelimbic/infralimbic/anterior cingulate inputs and human vmPFC/ACC circuitry. Instead, they provide limited contextual evidence:

- a parcel-level human coordinate-based meta-analytic summary of where stress-related terms are associated with reported activation density in the literature; and
- a compact clinical-background table summarizing ENIGMA findings in hippocampal, amygdalar, orbitofrontal, cingulate, and white-matter pathways relevant to stress psychopathology.

## Analysis 1: Neurosynth / NiMARE parcel summary

`neurosynth_coactivation.py`:

- downloads only the small Neurosynth v7 coordinates, metadata, and term-feature files via NiMARE;
- uses `MKDADensity` term-conditioned meta-analytic maps for `fear`, `threat`, `fear_conditioning`, `stress`, and `amygdala`;
- extracts parcel means from Harvard-Oxford cortical and subcortical atlases;
- defines a human vmPFC/ACC seed set from `Frontal Medial Cortex`, `Subcallosal Cortex`, `Paracingulate Gyrus`, `Cingulate Gyrus, anterior division`, and `Frontal Orbital Cortex`;
- computes a **pooled seed mean across both atlases combined**, then applies that same pooled seed mean to every parcel for a secondary `seed_scaled_activation_density` summary so subcortical parcels are not dropped;
- reports each term's parcel ranking separately as the primary output and keeps the mean across `fear`, `threat`, `fear_conditioning`, and `stress` only as a clearly labeled secondary summary;
- keeps `amygdala` as a separate diagnostic/reference term only, not as part of the main stress composite;
- does **not** run automatic mouse-human lexical matching, because a meaningful cross-species comparison requires a curated, literature-cited mapping defined by a domain expert before quantitative comparison is scientifically defensible.

### What the Neurosynth metric is and is not

The parcel scores here are **term-associated activation-density summaries** from a coordinate-based meta-analysis. The secondary `seed_scaled_activation_density` column multiplies each parcel mean by a single pooled vmPFC/ACC seed mean for that term. Because that multiplier is constant within a term, it does **not** change within-term parcel ordering and should **not** be described as seed-based coactivation, functional connectivity, structural connectivity, or anatomical coupling.

### Important caveats

- Coordinate-based meta-analysis is subject to publication bias, selective reporting, and term-annotation bias.
- Neurosynth term filters are not validated task ontologies; `fear_conditioning` here is only an approximate co-occurrence query requiring both `fear` and `conditioning` to appear in the annotation table.
- These parcel summaries cannot infer anatomical projections, axonal afferents, synaptic coupling, or true human functional connectivity.
- They cannot establish any human analogue of the single-cell or population-level multivalence coding measured in the mouse calcium-imaging data.
- Any eventual manuscript should position this analysis as translational context / hypothesis generation, **not** as validation on par with the mouse circuit model or ketamine causal manipulation.

### Run

```powershell
C:\path\to\python.exe BrainBeam\statistics\human_comparison\neurosynth_coactivation.py
```

Optional arguments:

- `--output-csv C:\path\to\human_vmPFC_acc_term_associated_activation_rankings.csv`
- `--detail-csv C:\path\to\neurosynth_term_activation_details.csv`

## Analysis 2: ENIGMA convergence table

`build_enigma_table.py` writes `enigma_convergence_table.csv` from directly verifiable summary statistics reported in ENIGMA PTSD/MDD abstracts or open full-text tables. Only published numbers that were explicitly confirmed are included. The table currently has 42 rows (30 PTSD, 12 MDD) drawn from 4 papers (Schmaal et al. 2016/2017, Logue et al. 2018, Dennis et al. 2021, Wang et al. 2021). Every row's effect size, sample size, and significance value was independently re-fetched and adversarially re-verified against the primary PMC source by a second agent before being added; no new papers or estimated/interpolated numbers were introduced during the expansion.

### ENIGMA caveat

These ENIGMA PTSD/MDD case-control morphometry findings do **not** measure stimulus multivalence, vmPFC/ACC afferent architecture, or seed-based connectivity. They should be presented as **clinical background context**, not as quantitative corroboration of the mouse connectomic, CORT, or ketamine results.

### Run

```powershell
C:\path\to\python.exe BrainBeam\statistics\human_comparison\build_enigma_table.py
```

## Figures

`make_figures.py` reads the existing CSV outputs and writes `.png` figures to `BrainBeam\statistics\human_comparison\figures\`:

- `vmPFC_ACC_activation_density_ranked_bar.png` - horizontal ranking of the top non-seed human parcels by the **secondary** mean seed-scaled activation-density summary across `fear`, `threat`, `fear_conditioning`, and `stress`.
- `vmPFC_ACC_activation_density_term_heatmap.png` - term-by-region heatmap for those top-ranked parcels, keeping `amygdala` as a diagnostic/reference column rather than folding it into the main composite.
- `vmPFC_ACC_activation_density_brain_slices.png` - orthographic Nilearn slice renderings that back-project parcel `activation_density_mean_z` values onto the combined Harvard-Oxford cortical + subcortical atlas for `fear`, `threat`, `fear_conditioning`, `stress`, and their mean.
- `vmPFC_ACC_activation_density_glass_brain.png` - transparent glass-brain projections of the same parcelwise activation-density maps.
- `enigma_effect_size_forest.png` - lollipop/forest-style plot of the curated ENIGMA PTSD/MDD effect sizes.
- `enigma_convergence_table.png` - compact figure-table rendering of the ENIGMA convergence CSV for supplemental display.
- `enigma_effect_size_brain_slices.png` - an optional within-human atlas rendering of the subset of ENIGMA rows with explicit Harvard-Oxford parcel mappings; unmatched rows are skipped and bilateral cortical parcel labels necessarily collapse laterality.

### Run

```powershell
C:\path\to\python.exe BrainBeam\statistics\human_comparison\make_figures.py
```

## Outputs

- `human_vmPFC_acc_term_associated_activation_rankings.csv`
- `neurosynth_term_activation_details.csv`
- `enigma_convergence_table.csv`
- `figures\vmPFC_ACC_activation_density_ranked_bar.png`
- `figures\vmPFC_ACC_activation_density_term_heatmap.png`
- `figures\vmPFC_ACC_activation_density_brain_slices.png`
- `figures\vmPFC_ACC_activation_density_glass_brain.png`
- `figures\enigma_effect_size_forest.png`
- `figures\enigma_convergence_table.png`
- `figures\enigma_effect_size_brain_slices.png`
- `AGENT_LOG.md`

## Interpretation summary

- Mouse-to-human region homology is approximate even for vmPFC/ACC-adjacent structures, and far more uncertain outside canonical limbic/cingulate correspondences.
- No automatic mouse-human parcel crosswalk is used here; curated cross-species mapping is a prerequisite future task.
- The Neurosynth analysis is literature-scale coordinate-based context, not tract tracing, projection mapping, or direct connectivity analysis.
- ENIGMA effect sizes mix Cohen's `d` and standardized regression coefficients depending on what each paper reported.
- The ENIGMA brain-rendered figure uses only explicit within-human atlas mappings and should be read as a sparse visual aid, not a comprehensive anatomical recoding of the literature table.
- Taken together, these materials should be framed as supportive translational context only.
