#!/usr/bin/env python3
"""Build parcel-level human term-associated activation rankings from small Neurosynth releases.

This workflow uses the small Neurosynth v7 term-annotation release distributed via
NiMARE, not raw fMRI downloads. For each term of interest, it fits a
term-conditioned MKDA density map, averages the resulting z-statistics within
Harvard-Oxford cortical and subcortical parcels, and reports parcel-level
term-associated activation-density summaries.

The vmPFC/ACC seed set is used only to compute a pooled seed mean per term and a
secondary seed-scaled activation-density column. That seed-scaled summary is not
functional connectivity, structural connectivity, or a true seed-based
coactivation estimate; because the seed multiplier is constant within each term,
it does not change within-term parcel ordering.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

try:
    from nilearn import datasets, image
    from nimare.extract import fetch_neurosynth
    from nimare.meta.cbma.mkda import MKDADensity
except ImportError as exc:  # pragma: no cover - import guard for user environments
    raise SystemExit(
        "This script requires nilearn and nimare. Install them before running."
    ) from exc


TERM_LABELS = {
    "fear": ["terms_abstract_tfidf__fear"],
    "threat": ["terms_abstract_tfidf__threat"],
    "fear_conditioning": [
        "terms_abstract_tfidf__fear",
        "terms_abstract_tfidf__conditioning",
    ],
    "stress": ["terms_abstract_tfidf__stress"],
    "amygdala": ["terms_abstract_tfidf__amygdala"],
}
PRIMARY_COMPOSITE_TERMS = ("fear", "threat", "fear_conditioning", "stress")
VM_PFC_ACC_SEED_LABELS = {
    "Frontal Medial Cortex",
    "Subcallosal Cortex",
    "Paracingulate Gyrus",
    "Cingulate Gyrus, anterior division",
    "Frontal Orbital Cortex",
}
CROSS_SPECIES_MAPPING_STATUS = "requires_curated_domain_expert_mapping"
CROSS_SPECIES_MAPPING_NOTE = (
    "Automatic lexical mouse-human matching is disabled. A scientifically meaningful "
    "cross-species comparison requires a curated, literature-cited mapping defined "
    "by a domain expert before quantitative comparison is attempted."
)


@dataclass(frozen=True)
class AtlasSpec:
    """Container for deterministic atlas metadata."""

    name: str
    image_obj: object
    labels: list[str]


def default_paths() -> dict[str, Path]:
    """Return script-local default input and output paths."""

    base_dir = Path(__file__).resolve().parent
    return {
        "base_dir": base_dir,
        "cache_dir": base_dir / "data_cache",
        "output_csv": base_dir / "human_vmPFC_acc_term_associated_activation_rankings.csv",
        "detail_csv": base_dir / "neurosynth_term_activation_details.csv",
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    paths = default_paths()
    parser = argparse.ArgumentParser(
        description=(
            "Build parcel-level human term-associated activation-density rankings "
            "from small Neurosynth releases."
        )
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=paths["cache_dir"],
        help="Directory for NiMARE/Nilearn downloads and cache files.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=paths["output_csv"],
        help="Wide ranking output CSV path.",
    )
    parser.add_argument(
        "--detail-csv",
        type=Path,
        default=paths["detail_csv"],
        help="Long-form per-term parcel detail CSV path.",
    )
    return parser.parse_args()


def load_neurosynth_dataset(cache_dir: Path):
    """Fetch the small Neurosynth term release and return a legacy Dataset."""

    cache_dir.mkdir(parents=True, exist_ok=True)
    return fetch_neurosynth(
        data_dir=str(cache_dir),
        version="7",
        source="abstract",
        vocab="terms",
        return_type="dataset",
    )[0]


def load_atlases(cache_dir: Path) -> list[AtlasSpec]:
    """Fetch Harvard-Oxford cortical and subcortical deterministic atlases."""

    cortical = datasets.fetch_atlas_harvard_oxford(
        "cort-maxprob-thr25-2mm", data_dir=str(cache_dir)
    )
    subcortical = datasets.fetch_atlas_harvard_oxford(
        "sub-maxprob-thr25-2mm", data_dir=str(cache_dir)
    )
    return [
        AtlasSpec(
            name="harvard_oxford_cortical",
            image_obj=image.load_img(cortical.maps),
            labels=list(cortical.labels),
        ),
        AtlasSpec(
            name="harvard_oxford_subcortical",
            image_obj=image.load_img(subcortical.maps),
            labels=list(subcortical.labels),
        ),
    ]


def study_ids_for_term(annotations: pd.DataFrame, term_columns: Iterable[str]) -> list[str]:
    """Return study IDs where all requested Neurosynth term columns are present."""

    term_columns = list(term_columns)
    missing = [column for column in term_columns if column not in annotations.columns]
    if missing:
        raise KeyError(f"Missing Neurosynth annotation columns: {missing}")
    mask = annotations[term_columns].gt(0).all(axis=1)
    return annotations.loc[mask, "id"].tolist()


def extract_atlas_activation_rows(
    atlas: AtlasSpec, z_map, term_name: str, study_count: int, term_columns: list[str]
) -> pd.DataFrame:
    """Extract parcel summaries from one atlas for one term-conditioned MKDA map."""

    aligned_map = image.resample_to_img(
        z_map,
        atlas.image_obj,
        interpolation="continuous",
        force_resample=True,
        copy_header=True,
    )
    atlas_data = np.asarray(atlas.image_obj.get_fdata(), dtype=int)
    z_data = np.asarray(aligned_map.get_fdata(), dtype=float)

    rows = []
    for index, label in enumerate(atlas.labels):
        if index == 0:
            continue
        voxel_mask = atlas_data == index
        if not np.any(voxel_mask):
            continue
        rows.append(
            {
                "term": term_name,
                "term_study_count": study_count,
                "atlas": atlas.name,
                "region": label,
                "activation_density_mean_z": float(np.nanmean(z_data[voxel_mask])),
                "activation_density_peak_z": float(np.nanmax(z_data[voxel_mask])),
                "voxel_count": int(np.count_nonzero(voxel_mask)),
                "is_vmPFC_acc_seed": label in VM_PFC_ACC_SEED_LABELS,
                "term_columns": ", ".join(term_columns),
            }
        )

    return pd.DataFrame(rows)


def compute_term_activation_details(dataset, atlases: list[AtlasSpec]) -> pd.DataFrame:
    """Run MKDA maps for each term and extract parcel activation-density summaries."""

    annotations = dataset.annotations.copy()
    meta = MKDADensity()
    detail_frames: list[pd.DataFrame] = []

    for term_name, term_columns in TERM_LABELS.items():
        ids = study_ids_for_term(annotations, term_columns)
        if not ids:
            raise ValueError(f"No Neurosynth studies found for term '{term_name}'.")

        result = meta.fit(dataset.slice(ids))
        z_map = result.get_map("z")
        atlas_frames = [
            extract_atlas_activation_rows(atlas, z_map, term_name, len(ids), list(term_columns))
            for atlas in atlases
        ]
        term_df = pd.concat(atlas_frames, ignore_index=True)

        pooled_seed_mean = term_df.loc[
            term_df["is_vmPFC_acc_seed"], "activation_density_mean_z"
        ].mean()
        if pd.isna(pooled_seed_mean):
            raise ValueError(
                f"No vmPFC/ACC seed parcels were found for term '{term_name}'."
            )

        term_df["pooled_seed_activation_density_mean_z"] = float(pooled_seed_mean)
        # This is a seed-scaled parcel summary of term-associated MKDA density, not a
        # measure of functional/structural connectivity or genuine seed-based coupling.
        # The pooled vmPFC/ACC seed multiplier is constant within a term, so it rescales
        # parcel density without changing within-term parcel ordering.
        term_df["seed_scaled_activation_density"] = (
            term_df["activation_density_mean_z"]
            * term_df["pooled_seed_activation_density_mean_z"]
        )
        detail_frames.append(term_df)

    detail_df = pd.concat(detail_frames, ignore_index=True)
    non_seed_mask = ~detail_df["is_vmPFC_acc_seed"]
    detail_df["activation_density_rank_within_term"] = (
        detail_df.loc[non_seed_mask]
        .groupby("term")["activation_density_mean_z"]
        .rank(ascending=False, method="min")
    )
    detail_df["seed_scaled_activation_density_rank_within_term"] = (
        detail_df.loc[non_seed_mask]
        .groupby("term")["seed_scaled_activation_density"]
        .rank(ascending=False, method="min")
    )
    return detail_df


def build_activation_summary_table(detail_df: pd.DataFrame) -> pd.DataFrame:
    """Convert long-form parcel detail into a wide ranking table."""

    non_seed = detail_df.loc[~detail_df["is_vmPFC_acc_seed"]].copy()
    ranking_df = (
        non_seed[["atlas", "region"]]
        .drop_duplicates()
        .sort_values(["atlas", "region"], ignore_index=True)
    )

    for term_name in TERM_LABELS:
        term_rows = non_seed.loc[non_seed["term"] == term_name, [
            "atlas",
            "region",
            "term_study_count",
            "activation_density_mean_z",
            "activation_density_rank_within_term",
            "pooled_seed_activation_density_mean_z",
            "seed_scaled_activation_density",
            "seed_scaled_activation_density_rank_within_term",
        ]].rename(
            columns={
                "term_study_count": f"{term_name}_study_count",
                "activation_density_mean_z": f"{term_name}_activation_density_mean_z",
                "activation_density_rank_within_term": f"{term_name}_activation_density_rank",
                "pooled_seed_activation_density_mean_z": f"{term_name}_pooled_seed_activation_density_mean_z",
                "seed_scaled_activation_density": f"{term_name}_seed_scaled_activation_density",
                "seed_scaled_activation_density_rank_within_term": f"{term_name}_seed_scaled_activation_density_rank",
            }
        )
        ranking_df = ranking_df.merge(term_rows, on=["atlas", "region"], how="left")

    composite_columns = [f"{term}_seed_scaled_activation_density" for term in PRIMARY_COMPOSITE_TERMS]
    ranking_df["secondary_mean_primary_term_seed_scaled_activation_density"] = ranking_df[
        composite_columns
    ].mean(axis=1)
    ranking_df["secondary_rank_primary_term_seed_scaled_activation_density"] = ranking_df[
        "secondary_mean_primary_term_seed_scaled_activation_density"
    ].rank(ascending=False, method="min")
    ranking_df["cross_species_mapping_status"] = CROSS_SPECIES_MAPPING_STATUS
    ranking_df["cross_species_mapping_notes"] = CROSS_SPECIES_MAPPING_NOTE
    return ranking_df.sort_values(
        [
            "secondary_rank_primary_term_seed_scaled_activation_density",
            "atlas",
            "region",
        ],
        ignore_index=True,
    )


def main() -> None:
    """Run the parcel ranking workflow."""

    args = parse_args()
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    args.detail_csv.parent.mkdir(parents=True, exist_ok=True)

    dataset = load_neurosynth_dataset(args.cache_dir)
    atlases = load_atlases(args.cache_dir)
    detail_df = compute_term_activation_details(dataset, atlases)
    ranking_df = build_activation_summary_table(detail_df)

    detail_df.to_csv(args.detail_csv, index=False)
    ranking_df.to_csv(args.output_csv, index=False)

    print(f"Wrote detail table to: {args.detail_csv}")
    print(f"Wrote ranking table to: {args.output_csv}")
    print(
        "Cross-species mapping status: automatic lexical matching disabled; "
        "curated domain-expert mapping required before quantitative mouse-human comparison."
    )


if __name__ == "__main__":
    main()
