#!/usr/bin/env python3
"""Generate reader-friendly figures for the human comparison supplement.

These figures visualize parcel-level Neurosynth term-associated activation-density
summaries and curated ENIGMA case-control morphometry findings. They should be
presented as translational context only: neither analysis measures anatomical
projections, true functional connectivity, or the multivalent single-cell /
population coding phenomena quantified in the mouse calcium-imaging data.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import textwrap

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from nilearn import datasets, image, plotting


TERM_NAMES = ["fear", "threat", "fear_conditioning", "stress", "amygdala"]
PRIMARY_TERM_NAMES = ["fear", "threat", "fear_conditioning", "stress"]
BRAIN_MAP_NAMES = PRIMARY_TERM_NAMES + ["primary_term_mean"]
TERM_SCORE_COLUMNS = [f"{term}_seed_scaled_activation_density" for term in TERM_NAMES]
TERM_LABELS = {
    "fear": "Fear",
    "threat": "Threat",
    "fear_conditioning": "Fear conditioning\n(two-word co-occurrence)",
    "stress": "Stress",
    "amygdala": "Amygdala\n(reference only)",
    "primary_term_mean": "Mean primary\nterm score",
}
MODALITY_COLORS = {
    "cortical thickness": "#4C78A8",
    "cortical volume": "#F58518",
    "structural volume": "#54A24B",
    "white matter": "#B279A2",
}
DISORDER_MARKERS = {"PTSD": "o", "MDD": "s"}
ATLAS_COLORS = {
    "harvard_oxford_cortical": "#4C78A8",
    "harvard_oxford_subcortical": "#F58518",
}
PRIMARY_COMPOSITE_COLUMN = "secondary_mean_primary_term_seed_scaled_activation_density"
PRIMARY_COMPOSITE_RANK_COLUMN = "secondary_rank_primary_term_seed_scaled_activation_density"
ENIGMA_ATLAS_MAPPING = {
    "Hippocampus": [
        ("harvard_oxford_subcortical", "Left Hippocampus"),
        ("harvard_oxford_subcortical", "Right Hippocampus"),
    ],
    "Amygdala": [
        ("harvard_oxford_subcortical", "Left Amygdala"),
        ("harvard_oxford_subcortical", "Right Amygdala"),
    ],
    "Left lateral orbitofrontal gyrus": [
        ("harvard_oxford_cortical", "Frontal Orbital Cortex"),
    ],
    "Right lateral orbitofrontal gyrus": [
        ("harvard_oxford_cortical", "Frontal Orbital Cortex"),
    ],
    "Left caudal anterior cingulate cortex": [
        ("harvard_oxford_cortical", "Cingulate Gyrus, anterior division"),
    ],
    "Left rostral anterior cingulate cortex": [
        ("harvard_oxford_cortical", "Cingulate Gyrus, anterior division"),
    ],
    "Right rostral anterior cingulate cortex": [
        ("harvard_oxford_cortical", "Cingulate Gyrus, anterior division"),
    ],
    "Left medial orbitofrontal cortex": [
        ("harvard_oxford_cortical", "Frontal Medial Cortex"),
    ],
}


@dataclass(frozen=True)
class AtlasSpec:
    """Container for deterministic atlas metadata."""

    name: str
    image_obj: object
    labels: list[str]


def default_paths() -> dict[str, Path]:
    """Return default local paths for inputs and outputs."""

    base_dir = Path(__file__).resolve().parent
    return {
        "base_dir": base_dir,
        "cache_dir": base_dir / "data_cache",
        "ranking_csv": base_dir / "human_vmPFC_acc_term_associated_activation_rankings.csv",
        "detail_csv": base_dir / "neurosynth_term_activation_details.csv",
        "enigma_csv": base_dir / "enigma_convergence_table.csv",
        "figure_dir": base_dir / "figures",
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    paths = default_paths()
    parser = argparse.ArgumentParser(
        description="Create figures for the human comparison supplemental analysis."
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=paths["cache_dir"],
        help="Directory for Nilearn atlas downloads and cache files.",
    )
    parser.add_argument(
        "--ranking-csv",
        type=Path,
        default=paths["ranking_csv"],
        help="Path to human_vmPFC_acc_term_associated_activation_rankings.csv",
    )
    parser.add_argument(
        "--detail-csv",
        type=Path,
        default=paths["detail_csv"],
        help="Path to neurosynth_term_activation_details.csv",
    )
    parser.add_argument(
        "--enigma-csv",
        type=Path,
        default=paths["enigma_csv"],
        help="Path to enigma_convergence_table.csv",
    )
    parser.add_argument(
        "--figure-dir",
        type=Path,
        default=paths["figure_dir"],
        help="Directory where figure files should be written.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=15,
        help="Number of top-ranked regions to show in ranking plots.",
    )
    return parser.parse_args()


def require_columns(df: pd.DataFrame, columns: list[str], label: str) -> None:
    """Fail early if an input CSV is missing expected columns."""

    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"{label} is missing required columns: {missing}")


def configure_style() -> None:
    """Apply a repo-consistent plotting style."""

    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams["savefig.dpi"] = 300
    plt.rcParams["figure.dpi"] = 300
    plt.rcParams["axes.titlesize"] = 16
    plt.rcParams["axes.labelsize"] = 12


def load_inputs(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load all figure input tables."""

    ranking_df = pd.read_csv(args.ranking_csv)
    detail_df = pd.read_csv(args.detail_csv)
    enigma_df = pd.read_csv(args.enigma_csv)

    require_columns(
        ranking_df,
        ["region", "atlas", PRIMARY_COMPOSITE_COLUMN, PRIMARY_COMPOSITE_RANK_COLUMN]
        + TERM_SCORE_COLUMNS,
        "Ranking CSV",
    )
    require_columns(
        detail_df,
        [
            "term",
            "term_study_count",
            "atlas",
            "region",
            "activation_density_mean_z",
            "seed_scaled_activation_density",
        ],
        "Detail CSV",
    )
    require_columns(
        enigma_df,
        ["disorder_group", "region", "modality", "effect_size", "effect_size_metric"],
        "ENIGMA CSV",
    )
    return ranking_df, detail_df, enigma_df


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


def atlas_arrays_in_base_space(atlases: list[AtlasSpec]):
    """Return a shared base atlas image plus per-atlas integer arrays."""

    base_img = atlases[0].image_obj
    atlas_arrays: dict[str, np.ndarray] = {}
    for atlas in atlases:
        atlas_img = atlas.image_obj
        if atlas_img.shape != base_img.shape or not np.allclose(atlas_img.affine, base_img.affine):
            atlas_img = image.resample_to_img(
                atlas_img,
                base_img,
                interpolation="nearest",
                force_resample=True,
                copy_header=True,
            )
        atlas_arrays[atlas.name] = np.asarray(atlas_img.get_fdata(), dtype=int)
    return base_img, atlas_arrays


def build_stat_map_from_scores(
    score_lookup: dict[tuple[str, str], float],
    base_img,
    atlases: list[AtlasSpec],
    atlas_arrays: dict[str, np.ndarray],
):
    """Assign parcel scores back into atlas voxels and return a NIfTI stat map."""

    stat_data = np.zeros(base_img.shape, dtype=float)
    for atlas in atlases:
        atlas_data = atlas_arrays[atlas.name]
        for label_index, label in enumerate(atlas.labels):
            if label_index == 0:
                continue
            score = score_lookup.get((atlas.name, label))
            if score is None or pd.isna(score):
                continue
            stat_data[atlas_data == label_index] = float(score)
    return image.new_img_like(base_img, stat_data)


def build_term_score_maps(
    detail_df: pd.DataFrame,
    base_img,
    atlases: list[AtlasSpec],
    atlas_arrays: dict[str, np.ndarray],
):
    """Build atlas-backprojected stat maps for primary Neurosynth terms and their mean."""

    score_maps: list[tuple[str, str, object]] = []
    score_values: list[float] = []

    for term_name in PRIMARY_TERM_NAMES:
        term_rows = detail_df.loc[detail_df["term"] == term_name]
        score_lookup = {
            (row.atlas, row.region): float(row.activation_density_mean_z)
            for row in term_rows.itertuples()
            if pd.notna(row.activation_density_mean_z)
        }
        score_values.extend(score_lookup.values())
        score_maps.append(
            (
                term_name,
                TERM_LABELS[term_name],
                build_stat_map_from_scores(score_lookup, base_img, atlases, atlas_arrays),
            )
        )

    primary_mean = (
        detail_df.loc[detail_df["term"].isin(PRIMARY_TERM_NAMES)]
        .pivot_table(
            index=["atlas", "region"],
            columns="term",
            values="activation_density_mean_z",
            aggfunc="first",
        )
        .assign(primary_term_mean=lambda frame: frame[PRIMARY_TERM_NAMES].mean(axis=1))
    )
    primary_mean_lookup = {
        key: float(value)
        for key, value in primary_mean["primary_term_mean"].to_dict().items()
        if pd.notna(value)
    }
    score_values.extend(primary_mean_lookup.values())
    score_maps.append(
        (
            "primary_term_mean",
            TERM_LABELS["primary_term_mean"],
            build_stat_map_from_scores(primary_mean_lookup, base_img, atlases, atlas_arrays),
        )
    )

    return score_maps, max(abs(value) for value in score_values if pd.notna(value))


def add_plot_row(
    figure,
    plot_func,
    stat_maps: list[tuple[str, str, object]],
    vmax: float,
    output_path: Path,
    title: str,
    footer: str,
    plot_kwargs: dict,
) -> None:
    """Render a stacked nilearn plot figure with one row per stat map."""

    figure.suptitle(title, y=0.995, fontsize=18)
    top = 0.94
    row_height = 0.145 if len(stat_maps) >= 5 else 0.24
    gap = 0.028

    for row_index, (_, row_title, stat_map) in enumerate(stat_maps):
        bottom = top - (row_index + 1) * row_height - row_index * gap
        rect = [0.04, bottom, 0.92, row_height]
        plot_func(
            stat_map,
            figure=figure,
            axes=rect,
            annotate=False,
            black_bg=False,
            cmap="cold_hot",
            symmetric_cbar=True,
            vmax=vmax,
            colorbar=row_index == 0,
            title=row_title,
            **plot_kwargs,
        )

    figure.text(0.5, 0.012, footer, ha="center", va="bottom", fontsize=10)
    figure.savefig(output_path, bbox_inches="tight")
    plt.close(figure)


def make_activation_brain_slices(
    detail_df: pd.DataFrame,
    base_img,
    atlases: list[AtlasSpec],
    atlas_arrays: dict[str, np.ndarray],
    output_path: Path,
) -> None:
    """Render orthographic brain slices colored by parcel activation-density scores."""

    stat_maps, vmax = build_term_score_maps(detail_df, base_img, atlases, atlas_arrays)
    figure = plt.figure(figsize=(12, 15))
    add_plot_row(
        figure=figure,
        plot_func=plotting.plot_stat_map,
        stat_maps=stat_maps,
        vmax=vmax,
        output_path=output_path,
        title="Harvard-Oxford parcelwise term-associated activation density",
        footer=(
            "Each parcel is colored by its primary activation_density_mean_z value from the term-conditioned "
            "MKDA map; the final row is the mean across fear, threat, fear conditioning, and stress."
        ),
        plot_kwargs={"display_mode": "ortho", "cut_coords": (0, -12, 12)},
    )


def make_activation_glass_brain(
    detail_df: pd.DataFrame,
    base_img,
    atlases: list[AtlasSpec],
    atlas_arrays: dict[str, np.ndarray],
    output_path: Path,
) -> None:
    """Render glass-brain projections of parcel activation-density scores."""

    stat_maps, vmax = build_term_score_maps(detail_df, base_img, atlases, atlas_arrays)
    figure = plt.figure(figsize=(11.5, 14))
    add_plot_row(
        figure=figure,
        plot_func=plotting.plot_glass_brain,
        stat_maps=stat_maps,
        vmax=vmax,
        output_path=output_path,
        title="Glass-brain view of parcelwise term-associated activation density",
        footer=(
            "Transparent projections of the same parcelwise activation_density_mean_z maps shown above; "
            "fear conditioning remains an approximate two-word co-occurrence query."
        ),
        plot_kwargs={"display_mode": "lzry", "plot_abs": False},
    )


def build_enigma_score_maps(
    enigma_df: pd.DataFrame,
    base_img,
    atlases: list[AtlasSpec],
    atlas_arrays: dict[str, np.ndarray],
):
    """Build disorder-specific ENIGMA effect-size maps from explicit atlas mappings."""

    stat_maps: list[tuple[str, str, object]] = []
    score_values: list[float] = []
    mapping_summaries: list[str] = []

    for disorder in ["PTSD", "MDD"]:
        disorder_rows = enigma_df.loc[enigma_df["disorder_group"] == disorder]
        parcel_effects: dict[tuple[str, str], list[float]] = {}
        mapped_regions: list[str] = []
        skipped_regions: list[str] = []

        for row in disorder_rows.itertuples():
            mapped_parcels = ENIGMA_ATLAS_MAPPING.get(row.region)
            if not mapped_parcels:
                skipped_regions.append(row.region)
                continue
            mapped_regions.append(row.region)
            for parcel_key in mapped_parcels:
                parcel_effects.setdefault(parcel_key, []).append(float(row.effect_size))

        score_lookup = {
            parcel_key: float(np.mean(values)) for parcel_key, values in parcel_effects.items()
        }
        if not score_lookup:
            continue
        score_values.extend(score_lookup.values())
        stat_maps.append(
            (
                disorder,
                f"{disorder} mapped ENIGMA effect sizes",
                build_stat_map_from_scores(score_lookup, base_img, atlases, atlas_arrays),
            )
        )
        mapping_summaries.append(
            f"{disorder}: mapped {len(mapped_regions)} rows, skipped {len(skipped_regions)}"
        )

    vmax = max(abs(value) for value in score_values if pd.notna(value))
    return stat_maps, vmax, "; ".join(mapping_summaries)


def make_enigma_brain_slices(
    enigma_df: pd.DataFrame,
    base_img,
    atlases: list[AtlasSpec],
    atlas_arrays: dict[str, np.ndarray],
    output_path: Path,
) -> None:
    """Render brain slices for the subset of ENIGMA rows with explicit atlas mappings."""

    stat_maps, vmax, mapping_summary = build_enigma_score_maps(
        enigma_df, base_img, atlases, atlas_arrays
    )
    if not stat_maps:
        return
    figure = plt.figure(figsize=(12, 7.5))
    add_plot_row(
        figure=figure,
        plot_func=plotting.plot_stat_map,
        stat_maps=stat_maps,
        vmax=vmax,
        output_path=output_path,
        title="Explicitly mapped ENIGMA effect sizes on Harvard-Oxford parcels",
        footer=(
            f"Only rows with an explicit within-human atlas mapping were rendered ({mapping_summary}). "
            "Cortical laterality is collapsed where Harvard-Oxford provides a bilateral parcel label."
        ),
        plot_kwargs={"display_mode": "ortho", "cut_coords": (0, -12, 12)},
    )


def make_ranked_bar_chart(
    ranking_df: pd.DataFrame, detail_df: pd.DataFrame, output_path: Path, top_n: int
) -> None:
    """Plot top-ranked human regions by seed-scaled activation-density summary."""

    plot_df = (
        ranking_df.sort_values(PRIMARY_COMPOSITE_RANK_COLUMN)
        .head(top_n)
        .copy()
        .sort_values(PRIMARY_COMPOSITE_COLUMN, ascending=True)
    )
    plot_df["region_label"] = plot_df["region"].map(lambda value: textwrap.fill(str(value), 28))

    study_counts = (
        detail_df[["term", "term_study_count"]]
        .drop_duplicates()
        .set_index("term")["term_study_count"]
        .to_dict()
    )
    subtitle = (
        f"Fear n={study_counts.get('fear', 'NA')}, threat n={study_counts.get('threat', 'NA')}, "
        f"fear conditioning n={study_counts.get('fear_conditioning', 'NA')} (two-word co-occurrence), "
        f"stress n={study_counts.get('stress', 'NA')}"
    )

    fig, ax = plt.subplots(figsize=(11.5, 8.5))
    y_positions = np.arange(len(plot_df))
    colors = [ATLAS_COLORS.get(atlas, "#7F7F7F") for atlas in plot_df["atlas"]]
    ax.barh(
        y_positions,
        plot_df[PRIMARY_COMPOSITE_COLUMN],
        color=colors,
        edgecolor="black",
        linewidth=0.6,
    )
    ax.set_yticks(y_positions)
    ax.set_yticklabels(plot_df["region_label"])
    ax.set_xlabel("Secondary mean seed-scaled term-associated activation density")
    ax.set_ylabel("")
    ax.set_title(
        "Top human parcels by secondary mean\nseed-scaled term-associated activation density"
    )
    ax.text(
        0.0,
        1.02,
        subtitle,
        transform=ax.transAxes,
        fontsize=10,
        ha="left",
        va="bottom",
    )
    for y_position, value in zip(y_positions, plot_df[PRIMARY_COMPOSITE_COLUMN].tolist()):
        ax.text(
            value + 0.15,
            y_position,
            f"{value:.2f}",
            va="center",
            fontsize=9,
        )
    legend_handles = [
        plt.Rectangle(
            (0, 0),
            1,
            1,
            facecolor=color,
            edgecolor="black",
            label=label.replace("harvard_oxford_", "").replace("_", " ").title(),
        )
        for label, color in ATLAS_COLORS.items()
        if label in plot_df["atlas"].unique()
    ]
    if legend_handles:
        ax.legend(
            handles=legend_handles,
            title="Atlas",
            loc="lower right",
            fontsize=9,
            title_fontsize=10,
            frameon=True,
        )
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def make_term_heatmap(ranking_df: pd.DataFrame, output_path: Path, top_n: int) -> None:
    """Plot term-by-region heatmap for the top-ranked parcels."""

    plot_df = ranking_df.sort_values(PRIMARY_COMPOSITE_RANK_COLUMN).head(top_n).copy()
    plot_df["region_label"] = plot_df["region"].map(lambda value: textwrap.fill(str(value), 24))
    heatmap_df = plot_df.set_index("region_label")[
        [f"{term}_seed_scaled_activation_density" for term in TERM_NAMES]
    ]
    heatmap_df = heatmap_df.rename(
        columns={f"{term}_seed_scaled_activation_density": TERM_LABELS[term] for term in TERM_NAMES}
    )

    fig, ax = plt.subplots(figsize=(11, max(6, 0.42 * len(heatmap_df) + 2.6)))
    heatmap_array = heatmap_df.to_numpy(dtype=float)
    image_obj = ax.imshow(heatmap_array, cmap="magma_r", aspect="auto")
    ax.set_xticks(np.arange(len(heatmap_df.columns)))
    ax.set_xticklabels(heatmap_df.columns)
    ax.set_yticks(np.arange(len(heatmap_df.index)))
    ax.set_yticklabels(heatmap_df.index)
    finite_max = np.nanmax(heatmap_array)
    threshold = finite_max * 0.55 if np.isfinite(finite_max) else 0
    for row_index in range(heatmap_array.shape[0]):
        for column_index in range(heatmap_array.shape[1]):
            ax.text(
                column_index,
                row_index,
                f"{heatmap_array[row_index, column_index]:.1f}",
                ha="center",
                va="center",
                fontsize=8,
                color="white" if heatmap_array[row_index, column_index] < threshold else "black",
            )
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_title(
        "Term-specific seed-scaled activation-density profile\n"
        "for top-ranked human parcels"
    )
    colorbar = fig.colorbar(image_obj, ax=ax, fraction=0.035, pad=0.02)
    colorbar.set_label("Seed-scaled term-associated activation density")
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def make_enigma_forest_plot(enigma_df: pd.DataFrame, output_path: Path) -> None:
    """Plot published ENIGMA effect sizes as clinical background context."""

    plot_df = enigma_df.copy().sort_values(["disorder_group", "effect_size", "region"])
    plot_df["label"] = plot_df.apply(
        lambda row: textwrap.fill(
            f"{row['disorder_group']} | {row['region']} | {row['modality']}", 42
        ),
        axis=1,
    )
    plot_df = plot_df.reset_index(drop=True)
    plot_df["y"] = np.arange(len(plot_df))

    fig_height = max(6, 0.55 * len(plot_df) + 1.4)
    fig, ax = plt.subplots(figsize=(11.5, fig_height))
    ax.axvline(0, color="black", linestyle="--", linewidth=1)

    for _, row in plot_df.iterrows():
        color = MODALITY_COLORS.get(row["modality"], "#777777")
        marker = DISORDER_MARKERS.get(row["disorder_group"], "o")
        ax.hlines(row["y"], xmin=0, xmax=row["effect_size"], color=color, linewidth=2.5, alpha=0.85)
        ax.scatter(
            row["effect_size"],
            row["y"],
            color=color,
            marker=marker,
            s=90,
            edgecolor="black",
            linewidth=0.5,
            zorder=3,
        )
        ax.text(
            row["effect_size"] - 0.005,
            row["y"] + 0.18,
            f"{row['effect_size']:.3f}",
            ha="right",
            va="bottom",
            fontsize=9,
        )

    ax.set_yticks(plot_df["y"])
    ax.set_yticklabels(plot_df["label"], fontsize=9)
    ax.set_xlabel("Published effect size")
    ax.set_ylabel("")
    ax.set_title("ENIGMA PTSD/MDD findings as clinical background context")

    modality_handles = [
        plt.Line2D([0], [0], marker="o", color=color, linestyle="", markersize=8, label=label)
        for label, color in MODALITY_COLORS.items()
        if label in plot_df["modality"].unique()
    ]
    disorder_handles = [
        plt.Line2D(
            [0],
            [0],
            marker=marker,
            color="white",
            markerfacecolor="gray",
            markeredgecolor="black",
            linestyle="",
            markersize=8,
            label=label,
        )
        for label, marker in DISORDER_MARKERS.items()
        if label in plot_df["disorder_group"].unique()
    ]
    legend_one = ax.legend(
        handles=modality_handles,
        title="Modality",
        loc="lower right",
        frameon=True,
        fontsize=9,
        title_fontsize=10,
    )
    ax.add_artist(legend_one)
    ax.legend(
        handles=disorder_handles,
        title="Disorder",
        loc="upper right",
        frameon=True,
        fontsize=9,
        title_fontsize=10,
    )

    plt.tight_layout()
    plt.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def make_enigma_table_figure(enigma_df: pd.DataFrame, output_path: Path) -> None:
    """Render a compact table-like figure for the ENIGMA background rows."""

    table_df = enigma_df.copy()
    table_df["effect_display"] = table_df.apply(
        lambda row: f"{row['effect_size']:.3f} ({row['effect_size_metric']})", axis=1
    )
    table_df["region"] = table_df["region"].map(lambda value: textwrap.fill(str(value), 30))
    table_df["modality"] = table_df["modality"].map(lambda value: textwrap.fill(str(value), 18))
    table_df = table_df[
        ["disorder_group", "region", "modality", "effect_display", "sample_size"]
    ].rename(
        columns={
            "disorder_group": "Disorder",
            "region": "Region",
            "modality": "Modality",
            "effect_display": "Effect size",
            "sample_size": "Sample",
        }
    )

    fig_height = max(5.5, 0.55 * len(table_df) + 1.8)
    fig, ax = plt.subplots(figsize=(14, fig_height))
    ax.axis("off")

    cell_text = table_df.values.tolist()
    col_labels = table_df.columns.tolist()
    table = ax.table(
        cellText=cell_text,
        colLabels=col_labels,
        loc="center",
        cellLoc="left",
        colLoc="left",
        bbox=[0, 0, 1, 0.93],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8.5)
    table.scale(1, 1.42)

    for (row_index, col_index), cell in table.get_celld().items():
        if row_index == 0:
            cell.set_facecolor("#D9E2F3")
            cell.set_text_props(weight="bold")
            continue
        disorder = table_df.iloc[row_index - 1]["Disorder"]
        base_color = "#FDEDEC" if disorder == "PTSD" else "#EAF2F8"
        if col_labels[col_index] == "Effect size":
            cell.set_facecolor("#F9E79F")
        else:
            cell.set_facecolor(base_color)

    ax.set_title(
        "Compact ENIGMA PTSD/MDD table (clinical context, not circuit validation)",
        fontsize=15,
        pad=18,
    )
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    """Generate the reader-facing supplemental figures."""

    args = parse_args()
    args.figure_dir.mkdir(parents=True, exist_ok=True)
    configure_style()
    ranking_df, detail_df, enigma_df = load_inputs(args)
    atlases = load_atlases(args.cache_dir)
    base_img, atlas_arrays = atlas_arrays_in_base_space(atlases)

    outputs = [
        args.figure_dir / "vmPFC_ACC_activation_density_ranked_bar.png",
        args.figure_dir / "vmPFC_ACC_activation_density_term_heatmap.png",
        args.figure_dir / "vmPFC_ACC_activation_density_brain_slices.png",
        args.figure_dir / "vmPFC_ACC_activation_density_glass_brain.png",
        args.figure_dir / "enigma_effect_size_forest.png",
        args.figure_dir / "enigma_convergence_table.png",
        args.figure_dir / "enigma_effect_size_brain_slices.png",
    ]

    make_ranked_bar_chart(ranking_df, detail_df, outputs[0], args.top_n)
    make_term_heatmap(ranking_df, outputs[1], args.top_n)
    make_activation_brain_slices(detail_df, base_img, atlases, atlas_arrays, outputs[2])
    make_activation_glass_brain(detail_df, base_img, atlases, atlas_arrays, outputs[3])
    make_enigma_forest_plot(enigma_df, outputs[4])
    make_enigma_table_figure(enigma_df, outputs[5])
    make_enigma_brain_slices(enigma_df, base_img, atlases, atlas_arrays, outputs[6])

    for output in outputs:
        print(f"Wrote figure: {output}")


if __name__ == "__main__":
    main()
