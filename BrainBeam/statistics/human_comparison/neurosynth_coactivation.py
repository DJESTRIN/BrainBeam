#!/usr/bin/env python3
"""Build a human vmPFC/ACC coactivation ranking from small Neurosynth releases.

This script uses the small Neurosynth v7 term-annotation release distributed via
NiMARE, not raw fMRI downloads. For each term of interest, it fits a
term-conditioned MKDA density map, averages the resulting z-statistics within
Harvard-Oxford cortical and subcortical parcels, and ranks non-seed parcels by
their coactivation proxy with a vmPFC/ACC seed set.

If a mouse `*_connection_distances.csv` output is available, the script adds a
lightweight keyword-based cross-reference column so the human ranking is ready
to compare against mouse afferent candidates. If no mouse CSV exists, the
script still completes and marks the comparison as pending mouse-side output.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
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

SEED_LABELS = {
    "Frontal Medial Cortex",
    "Subcallosal Cortex",
    "Paracingulate Gyrus",
    "Cingulate Gyrus, anterior division",
    "Frontal Orbital Cortex",
}

KEYWORD_GROUPS = {
    "amygdala": ("amygdala",),
    "hippocampus": ("hippocamp", "dentate", "subiculum", "entorhinal", "parahippocamp"),
    "cingulate": ("cingulate", "acc"),
    "orbitofrontal": ("orbitofrontal", "orbital", "ofc"),
    "insula": ("insula", "insular", "claustr"),
    "thalamus": ("thalam",),
    "striatum": ("caudate", "putamen", "striat", "accumbens", "pallid"),
    "septal": ("sept",),
    "temporal": ("temporal", "auditory"),
}


@dataclass(frozen=True)
class AtlasSpec:
    """Container for deterministic atlas metadata."""

    name: str
    image_obj: object
    labels: list[str]


def default_paths() -> dict[str, Path]:
    """Return script-local default input and output paths."""

    base_dir = Path(__file__).resolve().parent
    repo_root = Path(__file__).resolve().parents[3]
    return {
        "base_dir": base_dir,
        "repo_root": repo_root,
        "cache_dir": base_dir / "data_cache",
        "output_csv": base_dir / "human_vmPFC_acc_coactivation_rankings.csv",
        "detail_csv": base_dir / "neurosynth_term_region_details.csv",
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    paths = default_paths()
    parser = argparse.ArgumentParser(
        description="Build parcel-level human vmPFC/ACC coactivation rankings."
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
    parser.add_argument(
        "--mouse-csv",
        type=Path,
        default=None,
        help="Optional mouse `*_connection_distances.csv` output to cross-reference.",
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


def compute_term_detail(dataset, atlases: list[AtlasSpec]) -> pd.DataFrame:
    """Run MKDA maps for each term and extract parcel scores."""

    annotations = dataset.annotations.copy()
    meta = MKDADensity()
    detail_frames: list[pd.DataFrame] = []

    for term_name, term_columns in TERM_LABELS.items():
        ids = study_ids_for_term(annotations, term_columns)
        if not ids:
            raise ValueError(f"No Neurosynth studies found for term '{term_name}'.")

        result = meta.fit(dataset.slice(ids))
        z_map = result.get_map("z")

        for atlas in atlases:
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
                        "term_study_count": len(ids),
                        "atlas": atlas.name,
                        "region": label,
                        "mean_z": float(np.nanmean(z_data[voxel_mask])),
                        "max_z": float(np.nanmax(z_data[voxel_mask])),
                        "voxel_count": int(np.count_nonzero(voxel_mask)),
                        "is_vmPFC_acc_seed": label in SEED_LABELS,
                    }
                )

            atlas_df = pd.DataFrame(rows)
            seed_mean = atlas_df.loc[atlas_df["is_vmPFC_acc_seed"], "mean_z"].mean()
            atlas_df["seed_mean_z"] = float(seed_mean)
            atlas_df["coactivation_proxy"] = atlas_df["mean_z"] * atlas_df["seed_mean_z"]
            atlas_df["term_columns"] = ", ".join(term_columns)
            detail_frames.append(atlas_df)

    detail_df = pd.concat(detail_frames, ignore_index=True)
    detail_df["coactivation_rank_within_term"] = (
        detail_df.loc[~detail_df["is_vmPFC_acc_seed"]]
        .groupby("term")["coactivation_proxy"]
        .rank(ascending=False, method="min")
    )
    return detail_df


def normalized_text(text: str) -> str:
    """Normalize a region label for light keyword matching."""

    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def region_keywords(region_name: str) -> set[str]:
    """Map a region name to a coarse keyword set for mouse-human comparisons."""

    normalized = normalized_text(region_name)
    keywords = {token for token in normalized.split() if len(token) > 3}
    for group_name, markers in KEYWORD_GROUPS.items():
        if any(marker in normalized for marker in markers):
            keywords.add(group_name)
    return keywords


def find_mouse_csv(repo_root: Path) -> Path | None:
    """Auto-discover a mouse connection-distance CSV if one exists."""

    candidates = sorted(repo_root.glob("**/*connection_distances.csv"))
    return candidates[0] if candidates else None


def attach_mouse_cross_reference(ranking_df: pd.DataFrame, mouse_csv: Path | None) -> pd.DataFrame:
    """Add optional mouse cross-reference columns to the human ranking table."""

    output = ranking_df.copy()
    if mouse_csv is None or not mouse_csv.exists():
        output["mouse_source_file"] = ""
        output["mouse_cross_reference_status"] = "no_mouse_output_found"
        output["mouse_match_count"] = 0
        output["mouse_top_matches"] = ""
        output["mouse_best_connection_distance"] = np.nan
        output["mouse_best_projection_metric"] = np.nan
        return output

    mouse_df = pd.read_csv(mouse_csv)
    if "regionname" not in mouse_df.columns:
        output["mouse_source_file"] = str(mouse_csv)
        output["mouse_cross_reference_status"] = "mouse_csv_missing_regionname"
        output["mouse_match_count"] = 0
        output["mouse_top_matches"] = ""
        output["mouse_best_connection_distance"] = np.nan
        output["mouse_best_projection_metric"] = np.nan
        return output

    mouse_df = mouse_df.copy()
    mouse_df["normalized_regionname"] = mouse_df["regionname"].astype(str).map(normalized_text)
    mouse_df["keyword_set"] = mouse_df["regionname"].astype(str).map(region_keywords)

    sort_columns: list[str] = []
    ascending: list[bool] = []
    if "normalized_projection_volume" in mouse_df.columns:
        sort_columns.append("normalized_projection_volume")
        ascending.append(False)
    if "connection_distance" in mouse_df.columns:
        sort_columns.append("connection_distance")
        ascending.append(True)
    if sort_columns:
        mouse_df = mouse_df.sort_values(sort_columns, ascending=ascending, na_position="last")

    top_matches = []
    for _, row in output.iterrows():
        keywords = region_keywords(row["region"])
        match_scores = mouse_df["keyword_set"].map(lambda items: len(keywords.intersection(items)))
        matched = mouse_df.loc[match_scores > 0].copy()
        matched["match_score"] = match_scores[match_scores > 0]
        matched = matched.sort_values(
            ["match_score"] + sort_columns,
            ascending=[False] + ascending,
            na_position="last",
        )
        best = matched.head(5)
        top_matches.append(
            {
                "mouse_source_file": str(mouse_csv),
                "mouse_cross_reference_status": "matched" if not best.empty else "no_keyword_overlap",
                "mouse_match_count": int(len(best)),
                "mouse_top_matches": "; ".join(best["regionname"].astype(str).tolist()),
                "mouse_best_connection_distance": (
                    float(best.iloc[0]["connection_distance"])
                    if not best.empty and "connection_distance" in best.columns and pd.notna(best.iloc[0]["connection_distance"])
                    else np.nan
                ),
                "mouse_best_projection_metric": (
                    float(best.iloc[0]["normalized_projection_volume"])
                    if not best.empty and "normalized_projection_volume" in best.columns and pd.notna(best.iloc[0]["normalized_projection_volume"])
                    else np.nan
                ),
            }
        )

    return pd.concat([output.reset_index(drop=True), pd.DataFrame(top_matches)], axis=1)


def build_ranking_table(detail_df: pd.DataFrame, mouse_csv: Path | None) -> pd.DataFrame:
    """Convert long-form parcel detail into a wide ranking table."""

    non_seed = detail_df.loc[~detail_df["is_vmPFC_acc_seed"]].copy()
    ranking_df = non_seed.pivot_table(
        index=["atlas", "region"],
        columns="term",
        values="coactivation_proxy",
        aggfunc="first",
    ).reset_index()

    study_counts = (
        detail_df[["term", "term_study_count"]]
        .drop_duplicates()
        .set_index("term")["term_study_count"]
        .to_dict()
    )
    for term_name, study_count in study_counts.items():
        ranking_df[f"{term_name}_study_count"] = study_count

    ranking_df["mean_score_fear_threat_stress"] = ranking_df[
        ["fear", "threat", "fear_conditioning", "stress"]
    ].mean(axis=1)
    ranking_df["mean_score_all_terms"] = ranking_df[
        ["fear", "threat", "fear_conditioning", "stress", "amygdala"]
    ].mean(axis=1)
    ranking_df["rank_fear_threat_stress"] = ranking_df["mean_score_fear_threat_stress"].rank(
        ascending=False, method="min"
    )
    ranking_df["rank_all_terms"] = ranking_df["mean_score_all_terms"].rank(
        ascending=False, method="min"
    )
    ranking_df = ranking_df.sort_values(
        ["rank_fear_threat_stress", "rank_all_terms", "atlas", "region"]
    ).reset_index(drop=True)
    return attach_mouse_cross_reference(ranking_df, mouse_csv)


def main() -> None:
    """Run the parcel ranking workflow."""

    args = parse_args()
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    args.detail_csv.parent.mkdir(parents=True, exist_ok=True)

    paths = default_paths()
    dataset = load_neurosynth_dataset(args.cache_dir)
    atlases = load_atlases(args.cache_dir)
    detail_df = compute_term_detail(dataset, atlases)

    mouse_csv = args.mouse_csv or find_mouse_csv(paths["repo_root"])
    ranking_df = build_ranking_table(detail_df, mouse_csv)

    detail_df.to_csv(args.detail_csv, index=False)
    ranking_df.to_csv(args.output_csv, index=False)

    print(f"Wrote detail table to: {args.detail_csv}")
    print(f"Wrote ranking table to: {args.output_csv}")
    if mouse_csv and Path(mouse_csv).exists():
        print(f"Mouse cross-reference source: {mouse_csv}")
    else:
        print("Mouse cross-reference source: none found; outputs marked as pending mouse CSV.")


if __name__ == "__main__":
    main()
