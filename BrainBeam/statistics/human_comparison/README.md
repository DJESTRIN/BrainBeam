# Human comparison supplement

This folder contains supplemental analyses meant to place the mouse mPFC circuit findings in cautious human translational context. They are **hypothesis-generating supplements**, not validation analyses of comparable evidentiary strength to the mouse anatomy-weighted GLMM circuit model, the calcium-imaging multivalence results, or the ketamine causal-reversal experiment.

1. `neurosynth_coactivation.py` builds parcel-level human **term-associated activation-density** summaries for fear/threat/stress-related Neurosynth terms using the small term-annotation release distributed through NiMARE plus the bundled Harvard-Oxford atlas from Nilearn.
2. `build_enigma_table.py` compiles a literature-only ENIGMA PTSD/MDD convergence table from published summary statistics.
3. `make_figures.py` turns the generated CSV outputs into reader-facing figure panels for the supplement, including atlas-backprojected Nilearn brain renderings.
4. `mouse_human_rabies_correlation.py` is the **real quantitative comparison**: it aggregates actual mouse mPFC rabies-tracing input data (CORT vs. control) into anatomically-matched categories and compares the direction/magnitude of change against the ENIGMA effect sizes above.

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

## Analysis 3: Mouse rabies-tracing vs. human ENIGMA effect sizes (real quantitative comparison)

`mouse_human_rabies_correlation.py` uses actual mouse mPFC monosynaptic-input rabies-tracing data (channel 647, `normalizedcount`, 9 control vs. 7 usable CORT/stress mice after QC exclusion -- see below; source data at `C:\Users\listo\communal_registration_logcal_drop\rabies_experiment\{control,experimental}\df_tall.csv`, not tracked in this repo) and compares control-vs-CORT effect sizes (Cohen's d) against the ENIGMA table above, category by category.

**Data QC:** one nominal "CORT" subject (`4467196_5`) has near-zero rabies counts across **all four channels** (647/488/561/785), indicating a failed injection or registration rather than a genuine biological zero. This subject is automatically excluded (`load_mouse_data`'s QC filter, threshold on whole-brain total rawcount) before computing any group statistics; an earlier draft of this analysis omitted this check and included the failed subject, which measurably (though not qualitatively) inflated the CORT-vs-control effect sizes for every single region.

**Anatomical matching:** only regions with a defensible, literature-recognized mouse<->human homolog are compared (hippocampus, amygdala, ACC, OFC, insula, retrosplenial/PCC, accumbens, caudoputamen/caudate+putamen, thalamus, pallidum, lateral ventricle, and whole corpus callosum as a proxy for the human "tapetum" DTI label). Primate/gyral-pattern-specific regions added in the Wang 2021 expansion (precuneus, superior/middle temporal gyrus, superior/inferior parietal gyrus, banks of the superior temporal sulcus, lingual gyrus) have **no clear rodent homolog and are deliberately excluded** rather than force-matched. `mouse_rabies_region_manifest.csv` lists exactly which fine-grained Allen regions were pooled into each category, for auditing.

### Result (corrected run, QC-excluded subject + proper statistics) -- reported honestly, not spun

There are 12 anatomical categories, each compared against MDD and/or PTSD ENIGMA rows where available (21 category x disorder_group rows total, but these are **not 21 independent tests**: the mouse effect size is identical across MDD and PTSD within a category, since the mouse data has no disorder distinction). The honest primary statistic is therefore the **deduplicated per-category** agreement: **only 3 of 12 categories (25%) have the mouse and human effect fully agree in direction** (a two-sided exact binomial test against chance, p=0.5, gives p=0.146 -- not distinguishable from chance). 2 of the 12 categories (caudate+putamen, pallidum) have MDD and PTSD *disagree with each other* on direction, which only happens because the underlying human effect sizes for those regions are tiny/near-zero (e.g. Pallidum: MDD d=-0.001, PTSD d=+0.047) and therefore not a meaningful sign to test against in the first place. After Bonferroni correction across the 12 mouse category tests (alpha=0.0042), 3 categories (thalamus, pallidum, posterior cingulate/retrosplenial) show a statistically robust CORT-vs-control mouse effect, but even these do not consistently match the human effect direction.

**Sensitivity check:** re-running with `--value-column rawcount` (a non-compositional alternative to the default `normalizedcount`, which is a percent-of-subject-total measure and therefore not fully independent across regions) gives an even lower agreement rate (2/12 categories, with the binomial test now nominally below chance, p=0.039) -- i.e. the conclusion is not an artifact of using a compositional measure; if anything the compositional measure was slightly more favorable to convergence than the raw counts.

**Honest interpretation:** this analysis does **not** show meaningful cross-species convergence between the mouse CORT rabies-input changes and human ENIGMA PTSD/MDD structural effect sizes, and the corrected/more rigorous statistics make this conclusion stronger, not weaker, than an earlier draft of this analysis suggested. This could reflect any combination of: (1) a genuine construct-validity gap -- rabies-traced monosynaptic input strength (a connectivity measure) and structural MRI gray-matter volume (a very different modality) are not established in the literature to change in the same direction under stress/pathology, so a lack of agreement is not necessarily surprising; (2) the small mouse sample size (n=9 vs 7 after QC); (3) imperfect category matching (e.g. whole corpus callosum standing in for "tapetum," retrosplenial cortex standing in for PCC); or (4) the ENIGMA effect sizes themselves being very small (most |d| < 0.2, i.e. close to the noise floor to begin with). Report this as a genuine negative/null convergence check, not evidence either for or against the ENIGMA literature or the mouse data -- it must not be oversold as validation, and the same caution against treating any part of this supplement as validation-strength evidence applies here as well.

### Run

```powershell
C:\path\to\python.exe BrainBeam\statistics\human_comparison\mouse_human_rabies_correlation.py
```

Optional: `--value-column rawcount` to re-run the non-compositional sensitivity check described above.

## Figures

`make_figures.py` reads the existing CSV outputs and writes `.png` figures to `BrainBeam\statistics\human_comparison\figures\`:

- `vmPFC_ACC_activation_density_ranked_bar.png` - horizontal ranking of the top non-seed human parcels by the **secondary** mean seed-scaled activation-density summary across `fear`, `threat`, `fear_conditioning`, and `stress`.
- `vmPFC_ACC_activation_density_term_heatmap.png` - term-by-region heatmap for those top-ranked parcels, keeping `amygdala` as a diagnostic/reference column rather than folding it into the main composite.
- `vmPFC_ACC_activation_density_brain_slices.png` - orthographic Nilearn slice renderings that back-project parcel `activation_density_mean_z` values onto the combined Harvard-Oxford cortical + subcortical atlas for `fear`, `threat`, `fear_conditioning`, `stress`, and their mean.
- `vmPFC_ACC_activation_density_glass_brain.png` - transparent glass-brain projections of the same parcelwise activation-density maps.
- `enigma_effect_size_forest.png` - lollipop/forest-style plot of the curated ENIGMA PTSD/MDD effect sizes.
- `enigma_convergence_table.png` - compact figure-table rendering of the ENIGMA convergence CSV for supplemental display.
- `enigma_effect_size_brain_slices.png` - an optional within-human atlas rendering of the subset of ENIGMA rows with explicit Harvard-Oxford parcel mappings; unmatched rows are skipped and bilateral cortical parcel labels necessarily collapse laterality.
- `mouse_rabies_vs_enigma_comparison.png` - paired bar chart of human ENIGMA effect size vs. mouse rabies Cohen's d per matched category, colored by direction agreement.

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
- `figures\mouse_rabies_vs_enigma_comparison.png`
- `mouse_rabies_vs_enigma_comparison.csv`
- `mouse_rabies_region_manifest.csv`
- `AGENT_LOG.md`

## Interpretation summary

- Mouse-to-human region homology is approximate even for vmPFC/ACC-adjacent structures, and far more uncertain outside canonical limbic/cingulate correspondences.
- No automatic mouse-human parcel crosswalk is used here; curated cross-species mapping is a prerequisite future task.
- The Neurosynth analysis is literature-scale coordinate-based context, not tract tracing, projection mapping, or direct connectivity analysis.
- ENIGMA effect sizes mix Cohen's `d` and standardized regression coefficients depending on what each paper reported.
- The ENIGMA brain-rendered figure uses only explicit within-human atlas mappings and should be read as a sparse visual aid, not a comprehensive anatomical recoding of the literature table.
- **The real mouse-rabies-vs-ENIGMA quantitative comparison (Analysis 3), after excluding a QC-failed mouse subject and using the deduplicated per-category statistic, showed only 3/12 (25%) direction agreement (binomial p=0.146 vs. chance), dropping to 2/12 (17%, p=0.039) with a non-compositional sensitivity check -- this is a genuine null (if anything, below-chance) result for cross-species convergence, not a positive finding, and should be reported as such.**
- Taken together, these materials should be framed as supportive translational context only.
