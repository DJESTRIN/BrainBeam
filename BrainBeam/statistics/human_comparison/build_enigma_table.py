#!/usr/bin/env python3
"""Compile a small ENIGMA PTSD/MDD convergence table from verified sources.

This table is intended as clinical-background context only. ENIGMA case-control
morphometry findings do not directly measure stimulus multivalence, vmPFC/ACC
afferent architecture, or the causal circuit properties tested in the mouse
experiments, so they should not be treated as quantitative validation of the
mouse connectomic, CORT, or ketamine results.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    default_output = Path(__file__).resolve().parent / "enigma_convergence_table.csv"
    parser = argparse.ArgumentParser(
        description="Build a CSV of verified ENIGMA PTSD/MDD summary statistics."
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=default_output,
        help="Output CSV path.",
    )
    return parser.parse_args()


def build_rows() -> list[dict[str, str | float]]:
    """Return curated rows with directly verified summary statistics."""

    return [
        {
            "disorder_group": "PTSD",
            "region": "Hippocampus",
            "modality": "structural volume",
            "measure": "subcortical volume",
            "direction_of_effect": "smaller in current PTSD vs trauma-exposed controls",
            "effect_size": -0.17,
            "effect_size_metric": "Cohen's d",
            "sample_size": "794 PTSD / 1074 trauma-exposed controls (total 1868)",
            "source_citation": "Logue et al. 2018, Biol Psychiatry, doi:10.1016/j.biopsych.2017.09.006",
            "source_url": "https://pubmed.ncbi.nlm.nih.gov/29217296/",
            "notes": "Largest ENIGMA/PGC PTSD subcortical meta-analysis in the abstract.",
        },
        {
            "disorder_group": "PTSD",
            "region": "Amygdala",
            "modality": "structural volume",
            "measure": "subcortical volume",
            "direction_of_effect": "smaller in current PTSD vs trauma-exposed controls",
            "effect_size": -0.11,
            "effect_size_metric": "Cohen's d",
            "sample_size": "794 PTSD / 1074 trauma-exposed controls (total 1868)",
            "source_citation": "Logue et al. 2018, Biol Psychiatry, doi:10.1016/j.biopsych.2017.09.006",
            "source_url": "https://pubmed.ncbi.nlm.nih.gov/29217296/",
            "notes": "Abstract notes the amygdala result did not survive Bonferroni correction.",
        },
        {
            "disorder_group": "PTSD",
            "region": "Right lateral orbitofrontal gyrus",
            "modality": "cortical volume",
            "measure": "regional cortical volume",
            "direction_of_effect": "smaller in PTSD vs controls",
            "effect_size": -0.111,
            "effect_size_metric": "standardized coefficient",
            "sample_size": "1259 PTSD / 2079 controls",
            "source_citation": "Wang et al. 2021, Mol Psychiatry, doi:10.1038/s41380-020-00967-1",
            "source_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC8180531/",
            "notes": "Value verified from Table 2 of the open full text.",
        },
        {
            "disorder_group": "PTSD",
            "region": "Left lateral orbitofrontal gyrus",
            "modality": "cortical volume",
            "measure": "regional cortical volume",
            "direction_of_effect": "smaller in PTSD vs controls",
            "effect_size": -0.107,
            "effect_size_metric": "standardized coefficient",
            "sample_size": "1265 PTSD / 2089 controls",
            "source_citation": "Wang et al. 2021, Mol Psychiatry, doi:10.1038/s41380-020-00967-1",
            "source_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC8180531/",
            "notes": "Value verified from Table 2 of the open full text.",
        },
        {
            "disorder_group": "PTSD",
            "region": "Left caudal anterior cingulate cortex",
            "modality": "cortical volume",
            "measure": "regional cortical volume",
            "direction_of_effect": "smaller in PTSD vs controls",
            "effect_size": -0.098,
            "effect_size_metric": "standardized coefficient",
            "sample_size": "1266 PTSD / 2090 controls",
            "source_citation": "Wang et al. 2021, Mol Psychiatry, doi:10.1038/s41380-020-00967-1",
            "source_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC8180531/",
            "notes": "Value verified from Table 2 of the open full text.",
        },
        {
            "disorder_group": "PTSD",
            "region": "Left rostral anterior cingulate cortex",
            "modality": "cortical volume",
            "measure": "regional cortical volume",
            "direction_of_effect": "smaller in PTSD vs controls",
            "effect_size": -0.074,
            "effect_size_metric": "standardized coefficient",
            "sample_size": "1258 PTSD / 2090 controls",
            "source_citation": "Wang et al. 2021, Mol Psychiatry, doi:10.1038/s41380-020-00967-1",
            "source_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC8180531/",
            "notes": "Value verified from Table 2 of the open full text.",
        },
        {
            "disorder_group": "PTSD",
            "region": "Tapetum (corpus callosum)",
            "modality": "white matter",
            "measure": "fractional anisotropy",
            "direction_of_effect": "lower FA in PTSD vs controls",
            "effect_size": -0.11,
            "effect_size_metric": "Cohen's d",
            "sample_size": "1426 PTSD / 1621 controls (total 3047)",
            "source_citation": "Dennis et al. 2021, Mol Psychiatry, doi:10.1038/s41380-019-0631-x",
            "source_url": "https://pubmed.ncbi.nlm.nih.gov/31857689/",
            "notes": "Abstract emphasizes hippocampal interhemispheric white-matter relevance.",
        },
        {
            "disorder_group": "MDD",
            "region": "Hippocampus",
            "modality": "structural volume",
            "measure": "subcortical volume",
            "direction_of_effect": "smaller in MDD vs healthy controls",
            "effect_size": -0.14,
            "effect_size_metric": "Cohen's d",
            "sample_size": "1728 MDD / 7199 controls",
            "source_citation": "Schmaal et al. 2016, Mol Psychiatry, doi:10.1038/mp.2015.69",
            "source_url": "https://pubmed.ncbi.nlm.nih.gov/26122586/",
            "notes": "Abstract notes stronger effects in recurrent and early-onset MDD.",
        },
        {
            "disorder_group": "MDD",
            "region": "Left medial orbitofrontal cortex",
            "modality": "cortical thickness",
            "measure": "regional cortical thickness",
            "direction_of_effect": "thinner cortex in adult MDD vs controls",
            "effect_size": -0.134,
            "effect_size_metric": "Cohen's d",
            "sample_size": "1902 adult MDD / 7658 controls",
            "source_citation": "Schmaal et al. 2017, Mol Psychiatry, doi:10.1038/mp.2016.60",
            "source_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC5444023/",
            "notes": "Value verified from open full text Table 1; abstract adult sample size used.",
        },
        {
            "disorder_group": "MDD",
            "region": "Left rostral anterior cingulate cortex",
            "modality": "cortical thickness",
            "measure": "regional cortical thickness",
            "direction_of_effect": "thinner cortex in adult MDD vs controls",
            "effect_size": -0.130,
            "effect_size_metric": "Cohen's d",
            "sample_size": "1896 adult MDD / 7628 controls",
            "source_citation": "Schmaal et al. 2017, Mol Psychiatry, doi:10.1038/mp.2016.60",
            "source_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC5444023/",
            "notes": "Value verified from open full text Table 1.",
        },
        {
            "disorder_group": "MDD",
            "region": "Right rostral anterior cingulate cortex",
            "modality": "cortical thickness",
            "measure": "regional cortical thickness",
            "direction_of_effect": "thinner cortex in adult MDD vs controls",
            "effect_size": -0.098,
            "effect_size_metric": "Cohen's d",
            "sample_size": "1900 adult MDD / 7654 controls",
            "source_citation": "Schmaal et al. 2017, Mol Psychiatry, doi:10.1038/mp.2016.60",
            "source_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC5444023/",
            "notes": "Value verified from open full text Table 1.",
        },
    ]


def main() -> None:
    """Write the ENIGMA convergence CSV."""

    args = parse_args()
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(build_rows()).sort_values(
        ["disorder_group", "modality", "region"], ignore_index=True
    )
    df.to_csv(args.output_csv, index=False)
    print(f"Wrote ENIGMA convergence table to: {args.output_csv}")


if __name__ == "__main__":
    main()
