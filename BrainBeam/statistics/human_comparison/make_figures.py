#!/usr/bin/env python3
"""Generate reader-friendly figures for the human comparison supplement."""

from __future__ import annotations

import argparse
from pathlib import Path
import textwrap

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


TERM_COLUMNS = [
    "fear",
    "threat",
    "fear_conditioning",
    "stress",
    "amygdala",
]
TERM_LABELS = {
    "fear": "Fear",
    "threat": "Threat",
    "fear_conditioning": "Fear\nconditioning",
    "stress": "Stress",
    "amygdala": "Amygdala",
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


def default_paths() -> dict[str, Path]:
    """Return default local paths for inputs and outputs."""

    base_dir = Path(__file__).resolve().parent
    return {
        "base_dir": base_dir,
        "ranking_csv": base_dir / "human_vmPFC_acc_coactivation_rankings.csv",
        "detail_csv": base_dir / "neurosynth_term_region_details.csv",
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
        "--ranking-csv",
        type=Path,
        default=paths["ranking_csv"],
        help="Path to human_vmPFC_acc_coactivation_rankings.csv",
    )
    parser.add_argument(
        "--detail-csv",
        type=Path,
        default=paths["detail_csv"],
        help="Path to neurosynth_term_region_details.csv",
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
        help="Number of top coactivation regions to show in ranking plots.",
    )
    parser.add_argument(
        "--mouse-csv",
        type=Path,
        default=None,
        help=(
            "Optional mouse connection-distance CSV for the scaffolded mouse-vs-human "
            "comparison plot."
        ),
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
        ["region", "atlas", "mean_score_fear_threat_stress", "rank_fear_threat_stress"]
        + TERM_COLUMNS,
        "Ranking CSV",
    )
    require_columns(
        detail_df,
        ["term", "term_study_count", "region", "coactivation_proxy"],
        "Detail CSV",
    )
    require_columns(
        enigma_df,
        ["disorder_group", "region", "modality", "effect_size", "effect_size_metric"],
        "ENIGMA CSV",
    )
    return ranking_df, detail_df, enigma_df


def make_ranked_bar_chart(
    ranking_df: pd.DataFrame, detail_df: pd.DataFrame, output_path: Path, top_n: int
) -> None:
    """Plot top-ranked human regions by vmPFC/ACC coactivation strength."""

    plot_df = (
        ranking_df.sort_values("rank_fear_threat_stress")
        .head(top_n)
        .copy()
        .sort_values("mean_score_fear_threat_stress", ascending=True)
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
        f"fear conditioning n={study_counts.get('fear_conditioning', 'NA')}, "
        f"stress n={study_counts.get('stress', 'NA')}"
    )

    fig, ax = plt.subplots(figsize=(11, 8.5))
    y_positions = np.arange(len(plot_df))
    colors = [ATLAS_COLORS.get(atlas, "#7F7F7F") for atlas in plot_df["atlas"]]
    ax.barh(
        y_positions,
        plot_df["mean_score_fear_threat_stress"],
        color=colors,
        edgecolor="black",
        linewidth=0.6,
    )
    ax.set_yticks(y_positions)
    ax.set_yticklabels(plot_df["region_label"])
    ax.set_xlabel("Mean vmPFC/ACC coactivation proxy")
    ax.set_ylabel("")
    ax.set_title("Top human regions coactivating with vmPFC/ACC\nacross fear/threat/stress terms")
    ax.text(
        0.0,
        1.02,
        subtitle,
        transform=ax.transAxes,
        fontsize=10,
        ha="left",
        va="bottom",
    )
    for y_position, value in zip(y_positions, plot_df["mean_score_fear_threat_stress"].tolist()):
        ax.text(
            value + 0.15,
            y_position,
            f"{value:.2f}",
            va="center",
            fontsize=9,
        )
    legend_handles = [
        plt.Rectangle((0, 0), 1, 1, facecolor=color, edgecolor="black", label=label.replace("harvard_oxford_", "").replace("_", " ").title())
        for label, color in ATLAS_COLORS.items()
        if label in plot_df["atlas"].unique()
    ]
    if legend_handles:
        ax.legend(handles=legend_handles, title="Atlas", loc="lower right", fontsize=9, title_fontsize=10, frameon=True)
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def make_term_heatmap(ranking_df: pd.DataFrame, output_path: Path, top_n: int) -> None:
    """Plot a term-by-region heatmap for the top-ranked parcels."""

    plot_df = ranking_df.sort_values("rank_fear_threat_stress").head(top_n).copy()
    plot_df["region_label"] = plot_df["region"].map(lambda value: textwrap.fill(str(value), 24))
    heatmap_df = plot_df.set_index("region_label")[TERM_COLUMNS].rename(columns=TERM_LABELS)

    fig, ax = plt.subplots(figsize=(9.5, max(6, 0.42 * len(heatmap_df) + 2.4)))
    heatmap_array = heatmap_df.to_numpy(dtype=float)
    image = ax.imshow(heatmap_array, cmap="magma_r", aspect="auto")
    ax.set_xticks(np.arange(len(heatmap_df.columns)))
    ax.set_xticklabels(heatmap_df.columns)
    ax.set_yticks(np.arange(len(heatmap_df.index)))
    ax.set_yticklabels(heatmap_df.index)
    for row_index in range(heatmap_array.shape[0]):
        for column_index in range(heatmap_array.shape[1]):
            ax.text(
                column_index,
                row_index,
                f"{heatmap_array[row_index, column_index]:.1f}",
                ha="center",
                va="center",
                fontsize=8,
                color="white" if heatmap_array[row_index, column_index] < np.nanmax(heatmap_array) * 0.55 else "black",
            )
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_title("Term-specific human coactivation profile\nfor top vmPFC/ACC-linked regions")
    colorbar = fig.colorbar(image, ax=ax, fraction=0.035, pad=0.02)
    colorbar.set_label("Coactivation proxy")
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def make_enigma_forest_plot(enigma_df: pd.DataFrame, output_path: Path) -> None:
    """Plot published ENIGMA effect sizes by region and modality."""

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
    ax.set_title("ENIGMA PTSD/MDD convergence effects in stress-relevant human regions")

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
    """Render a compact table-like figure for the ENIGMA convergence rows."""

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
        "Compact ENIGMA convergence table for PTSD/MDD stress-circuit findings",
        fontsize=15,
        pad=18,
    )
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def keyword_group(region_name: str) -> str | None:
    """Map a region label to a coarse group for future mouse-human comparison plots."""

    normalized = str(region_name).lower()
    for group_name, markers in KEYWORD_GROUPS.items():
        if any(marker in normalized for marker in markers):
            return group_name
    return None


def make_mouse_human_comparison_scatter(
    ranking_df: pd.DataFrame, mouse_csv: Path, output_path: Path
) -> None:
    """Scaffolded cross-species plot for future mouse outputs."""

    mouse_df = pd.read_csv(mouse_csv)
    require_columns(mouse_df, ["regionname"], "Mouse comparison CSV")
    if (
        "normalized_projection_volume" not in mouse_df.columns
        and "connection_distance" not in mouse_df.columns
    ):
        raise ValueError(
            "Mouse comparison CSV needs normalized_projection_volume or connection_distance."
        )

    human_df = ranking_df.copy()
    human_df["group"] = human_df["region"].map(keyword_group)
    human_df = human_df.dropna(subset=["group"])
    if human_df.empty:
        raise ValueError("No human ranking regions mapped onto the scaffold keyword groups.")

    mouse_df = mouse_df.copy()
    mouse_df["group"] = mouse_df["regionname"].map(keyword_group)
    mouse_df = mouse_df.dropna(subset=["group"])
    if mouse_df.empty:
        raise ValueError("No mouse regions mapped onto the scaffold keyword groups.")

    human_summary = (
        human_df.groupby("group", as_index=False)["mean_score_fear_threat_stress"].mean()
        .rename(columns={"mean_score_fear_threat_stress": "human_score"})
    )

    if "normalized_projection_volume" in mouse_df.columns:
        mouse_summary = (
            mouse_df.groupby("group", as_index=False)["normalized_projection_volume"].max()
            .rename(columns={"normalized_projection_volume": "mouse_score"})
        )
        mouse_axis_label = "Mouse normalized projection volume"
    else:
        mouse_summary = (
            mouse_df.groupby("group", as_index=False)["connection_distance"].min()
            .assign(mouse_score=lambda frame: -frame["connection_distance"])
            .drop(columns=["connection_distance"])
        )
        mouse_axis_label = "Mouse proximity proxy (-connection distance)"

    comparison_df = human_summary.merge(mouse_summary, on="group", how="inner")
    if comparison_df.empty:
        raise ValueError("No overlapping keyword groups were available for comparison.")

    fig, ax = plt.subplots(figsize=(8, 6.5))
    ax.scatter(comparison_df["mouse_score"], comparison_df["human_score"], s=120, color="#4C78A8", edgecolor="black")
    for _, row in comparison_df.iterrows():
        ax.text(row["mouse_score"], row["human_score"] + 0.1, row["group"], fontsize=9, ha="center")
    ax.set_xlabel(mouse_axis_label)
    ax.set_ylabel("Mean human fear/threat/stress coactivation proxy")
    ax.set_title("Scaffolded mouse-vs-human region-group comparison")
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    """Generate the missing reader-facing figures."""

    args = parse_args()
    args.figure_dir.mkdir(parents=True, exist_ok=True)
    configure_style()
    ranking_df, detail_df, enigma_df = load_inputs(args)

    outputs = [
        args.figure_dir / "vmPFC_ACC_coactivation_ranked_bar.png",
        args.figure_dir / "vmPFC_ACC_coactivation_term_heatmap.png",
        args.figure_dir / "enigma_effect_size_forest.png",
        args.figure_dir / "enigma_convergence_table.png",
    ]

    make_ranked_bar_chart(ranking_df, detail_df, outputs[0], args.top_n)
    make_term_heatmap(ranking_df, outputs[1], args.top_n)
    make_enigma_forest_plot(enigma_df, outputs[2])
    make_enigma_table_figure(enigma_df, outputs[3])

    for output in outputs:
        print(f"Wrote figure: {output}")

    if args.mouse_csv and args.mouse_csv.exists():
        mouse_output = args.figure_dir / "mouse_vs_human_region_group_scatter.png"
        make_mouse_human_comparison_scatter(ranking_df, args.mouse_csv, mouse_output)
        print(f"Wrote figure: {mouse_output}")
    else:
        print(
            "Skipped mouse-vs-human scatter scaffold: no mouse CSV supplied. "
            "Function is implemented but not runnable until mouse output exists."
        )


if __name__ == "__main__":
    main()
