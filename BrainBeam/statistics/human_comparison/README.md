# Human comparison supplement

This folder contains two supplemental analyses for comparing the mouse mPFC connectomic findings to convergent human evidence:

1. `neurosynth_coactivation.py` builds parcel-level human meta-analytic rankings for fear/threat/stress-related terms using the small Neurosynth term-annotation release distributed through NiMARE plus the bundled Harvard-Oxford atlas from Nilearn.
2. `build_enigma_table.py` compiles a literature-only ENIGMA PTSD/MDD convergence table from published summary statistics.
3. `make_figures.py` turns the generated CSV outputs into reader-facing figure panels for the supplement.

## Why this exists

The eventual paper needs a cautious mouse-to-human bridge. These analyses do **not** claim one-to-one homology between mouse prelimbic/infralimbic/anterior cingulate inputs and human vmPFC/ACC circuitry. Instead, they provide convergent context:

- a human meta-analytic map-based ranking of regions that co-occur with vmPFC/ACC engagement for fear/threat/stress terms; and
- a compact human literature table summarizing ENIGMA findings in hippocampal, amygdalar, orbitofrontal, cingulate, and white-matter pathways relevant to stress psychopathology.

## Analysis 1: Neurosynth / NiMARE parcel ranking

`neurosynth_coactivation.py`:

- downloads only the small Neurosynth v7 coordinates/metadata/term-feature files via NiMARE;
- uses `MKDADensity` term-conditioned meta-analytic maps for `fear`, `threat`, `fear_conditioning`, `stress`, and `amygdala`;
- extracts parcel means from Harvard-Oxford cortical and subcortical atlases;
- defines a human vmPFC/ACC seed set from `Frontal Medial Cortex`, `Subcallosal Cortex`, `Paracingulate Gyrus`, `Cingulate Gyrus, anterior division`, and `Frontal Orbital Cortex`;
- ranks non-seed parcels by a term-specific coactivation proxy (`parcel mean z * vmPFC/ACC mean z`);
- optionally cross-references a mouse `*_connection_distances.csv` file if one exists.

### Important limitation

`BrainBeam\statistics\ConnectomicDistance.py` currently exports `connection_distance` and related ID columns, but it does **not** itself export parcel-level `normalized_projection_volume` values. The comparison script therefore treats mouse cross-referencing as optional and falls back to method-level readiness when no mouse output CSV is available.

### Run

```powershell
C:\path\to\python.exe BrainBeam\statistics\human_comparison\neurosynth_coactivation.py
```

Optional arguments:

- `--mouse-csv C:\path\to\mouse_connection_distances.csv`
- `--output-csv C:\path\to\human_vmPFC_acc_coactivation_rankings.csv`
- `--detail-csv C:\path\to\neurosynth_term_region_details.csv`

## Analysis 2: ENIGMA convergence table

`build_enigma_table.py` writes `enigma_convergence_table.csv` from directly verifiable summary statistics reported in ENIGMA PTSD/MDD abstracts or open full text tables. Only published numbers that were explicitly confirmed are included.

### Run

```powershell
C:\path\to\python.exe BrainBeam\statistics\human_comparison\build_enigma_table.py
```

## Figures

`make_figures.py` reads the existing CSV outputs and writes `.png` figures to `BrainBeam\statistics\human_comparison\figures\`:

- `vmPFC_ACC_coactivation_ranked_bar.png` — horizontal ranking of the top non-seed human parcels by mean vmPFC/ACC coactivation proxy across `fear`, `threat`, `fear_conditioning`, and `stress`.
- `vmPFC_ACC_coactivation_term_heatmap.png` — term-by-region heatmap for those top-ranked parcels, showing whether a region is driven broadly across terms or only by a subset.
- `enigma_effect_size_forest.png` — lollipop/forest-style plot of the curated ENIGMA PTSD/MDD effect sizes, with modality colors and disorder-specific markers.
- `enigma_convergence_table.png` — compact figure-table rendering of the ENIGMA convergence CSV for supplemental display.

### Run

```powershell
C:\path\to\python.exe BrainBeam\statistics\human_comparison\make_figures.py
```

Optional argument for the future cross-species comparison scaffold:

- `--mouse-csv C:\path\to\mouse_connection_distances.csv`

If a compatible mouse CSV is supplied later, `make_figures.py` also contains a scaffolded `mouse_vs_human_region_group_scatter.png` generator that aggregates broad region groups across species. That comparison is **not runnable yet in this folder's current state**, because no mouse `*_connection_distances.csv` output is present here yet.

## Outputs

- `human_vmPFC_acc_coactivation_rankings.csv`
- `neurosynth_term_region_details.csv`
- `enigma_convergence_table.csv`
- `figures\vmPFC_ACC_coactivation_ranked_bar.png`
- `figures\vmPFC_ACC_coactivation_term_heatmap.png`
- `figures\enigma_effect_size_forest.png`
- `figures\enigma_convergence_table.png`
- `AGENT_LOG.md`

## Interpretation caveats

- Mouse-to-human region homology is approximate, especially outside canonical ACC/vmPFC and limbic structures.
- The Neurosynth analysis is convergent evidence from literature-scale coordinate meta-analysis, not tract tracing or individual-subject connectivity.
- ENIGMA effect sizes mix Cohen's `d` and standardized regression coefficients depending on what each paper reported.
- These comparisons are supportive context for the mouse mPFC circuit results, not direct validation.
