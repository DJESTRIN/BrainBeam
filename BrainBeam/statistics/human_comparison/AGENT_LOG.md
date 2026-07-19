# AGENT_LOG

- 2026-07-19 19:17 EDT - Task started in `C:\Users\listo\BrainBeam-connectomic` from base branch `connectomic-distance-analysis`.
- Read `BrainBeam\statistics\ConnectomicDistance.py` first, per instructions. Key mouse output schema identified: region-level CSV includes original region/stat columns plus `id`, `connectivity_resolved_id`, and `connection_distance`; projections are afferent/upstream into mPFC seeds (PL/IL/ACC) using Allen `normalized_projection_volume` and hop distance.
- Inspected `BrainBeam\statistics\datasets\`; found Allen support files and projection search CSVs but no precomputed `*_connection_distances.csv` output available yet for direct mouse-human crosswalk.
- Worktree had many unrelated pre-existing untracked files; leaving them untouched and committing only new `human_comparison` files.
- 2026-07-19 19:19 EDT - Inspected repository dependency files (equirements.txt, setup.py) and confirmed no existing human-comparison outputs or *_connection_distances.csv mouse result files were present in the worktree.
- 2026-07-19 19:20 EDT - Tried python and py; neither was available on PATH beyond Windows Store stubs. Located a working interpreter at C:\Users\listo\engelhard_quicktest\venv\Scripts\python.exe; using that existing local venv for validation and data-fetch scripts because no repository-specific interpreter was on PATH.
- 2026-07-19 19:21 EDT - Downloaded NiMARE and all pip dependencies into BrainBeam\\statistics\\human_comparison\\package_audit first for size auditing before installation; detailed wheel sizes captured separately immediately after download.
- 2026-07-19 19:24 EDT - Installed NiMARE into a repository-local virtual environment at BrainBeam\\statistics\\human_comparison\\venv from the pre-downloaded wheels, avoiding changes to the unrelated shared engelhard_quicktest environment.
- 2026-07-19 19:24 EDT - Fetched the small Neurosynth v7 term-annotation release (source=abstract, ocab=terms) with NiMARE into BrainBeam\\statistics\\human_comparison\\data_cache\\neurosynth; exact file sizes logged separately immediately after download.
- 2026-07-19 19:27 EDT - Downloaded the bundled Harvard-Oxford cortical atlas with Nilearn for parcel-level ranking; this is a small atlas package from NITRC/FSL, well below the 10 GB cutoff, and exact archive size plus extracted-file sizes were logged separately.
- 2026-07-19 19:43 EDT - Created README.md, .gitignore, 
eurosynth_coactivation.py, and uild_enigma_table.py under BrainBeam\\statistics\\human_comparison.
- 2026-07-19 19:43 EDT - Noted an important schema nuance from ConnectomicDistance.py: the exported CSV includes id, connectivity_resolved_id, and connection_distance, but not an explicit parcel-level 
ormalized_projection_volume column, so the human comparison code treats mouse cross-reference as optional unless an enriched mouse table is supplied.
- 2026-07-19 19:44 EDT - Ran uild_enigma_table.py successfully and generated enigma_convergence_table.csv.
- 2026-07-19 19:45 EDT - Ran 
eurosynth_coactivation.py successfully and generated human_vmPFC_acc_coactivation_rankings.csv plus 
eurosynth_term_region_details.csv. The script auto-checked for *_connection_distances.csv mouse outputs and found none, so the human ranking was generated with mouse_cross_reference_status=no_mouse_output_found.
- 2026-07-19 19:46 EDT - Validated the generated human outputs by inspecting the CSV headers/top rows. The ranking output includes per-term scores, study counts, vmPFC/ACC aggregate means, and a 
o_mouse_output_found status because no mouse *_connection_distances.csv file exists yet in the worktree.
