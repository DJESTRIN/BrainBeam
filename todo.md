# Repo organization TODO

Tracking work to clean up stray csv/jpg/txt/log files scattered around the
repo and make sure pipeline code drops generated files in sensible places.

## Done
- [x] Added a root `.gitignore` covering `__pycache__/`, `*.pyc`, build
      artifacts, cluster job logs (`slurm-*.out`, `*.log`), and other cruft
      so generated files stop getting accidentally committed.
- [x] Untracked accidentally-committed junk: `gui/__pycache__/*.pyc`,
      `gui/slurm-123106.out` (a cluster job log), and
      `cayugatest_deleteme.json.json` (a pipeline run-state JSON that was
      committed by mistake — the filename itself says "deleteme").
- [x] Fixed `statistics/concat_tall_format.py` writing its combined dataset
      without a file extension (`to_csv("pseudorabies_dataset")` ->
      `to_csv("pseudorabies_dataset.csv")`).

## Notes / follow-up for a human to confirm
- `statistics/concat_tall_format.py` and `statistics/stats_to_atlas.py`
  intentionally `os.chdir()` into `/athena/listonlab/scratch/dje4001/...`
  before writing outputs. That's expected for this HPC pipeline (outputs are
  meant to live on scratch/store storage, not in the repo), so these were
  left alone beyond the extension fix above.
- During this session the working directory briefly showed a large,
  **untracked** duplicate directory tree at `BrainBeam/BrainBeam/...`
  (old-style modules like `BrainBeamStats.py`, `NetworkSimulation.py`,
  `AtlasOperations.py`, plus many loose `.csv`/`.jpg` outputs at the repo
  root) that does not match the current `integrate-linreg` branch's tracked
  `statistics/` package (`build_dataset.py`, `stats_to_atlas.py`,
  `linreg_bridge.py`, `concat_tall_format.py`, `princeton_ara.py`). That
  directory appeared to be actively changing/disappearing during this
  session (likely a stale leftover from an older checkout, or another
  concurrent process cleaning it up) and is not part of git history, so no
  automated changes were made to it. **Please confirm whether
  `BrainBeam/BrainBeam/` (if it still exists) can be deleted** — it looks
  like leftover clutter from before this branch's refactor, not current
  source.
- If more root-level generated files show up in the future (CSVs, JPGs,
  logs), prefer writing them under a script's own `datasets/`/`figures/`
  subfolder (see the pattern already used for atlas datasets), or to the
  external scratch directory, rather than the repo root or cwd.
