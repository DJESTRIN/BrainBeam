#!/usr/bin/env python3
"""Compare real mouse mPFC rabies-tracing (CORT vs. control) input strength
against published human ENIGMA PTSD/MDD structural effect sizes.

This is the first *real quantitative* mouse-vs-human comparison in this
supplement (as opposed to the earlier Neurosynth literature-term analysis).
It uses actual rabies monosynaptic-input tracing data from David Estrin's
mPFC CORT experiment, not a literature proxy.

IMPORTANT ANATOMICAL HONESTY NOTE: only regions with a defensible, commonly
cited mouse<->human anatomical correspondence are compared. Human cortical
regions with no clear rodent homolog (e.g. precuneus, superior/middle
temporal gyrus, superior/inferior parietal gyrus, banks of the superior
temporal sulcus, lingual gyrus -- all primate/gyral-pattern-specific
structures added in the Wang et al. 2021 ENIGMA table expansion) are
deliberately EXCLUDED from this comparison rather than force-matched. This
keeps the comparison anatomically defensible at the cost of a smaller
matched-region set; see README.md and AGENT_LOG.md for the rationale.

Mouse side: rabies-labeled monosynaptic input cell counts (channel 647,
`normalizedcount`), control (n=9) vs. CORT/stress (n=8) mice, summed across
ipsilateral+contralateral hemispheres per subject to give one bilateral
value per subject per region category, then compared with a two-sample
t-test / Cohen's d (same effect-size convention used elsewhere in this
repo's BrainBeamStats.gen().volcano()).

Human side: mean effect size across all `enigma_convergence_table.csv` rows
whose `region` matches the category (kept separate by disorder_group, since
MDD and PTSD are distinct conditions and should not be silently pooled).

STATISTICAL POWER CAVEAT (read before citing this analysis): with only
9 vs. 8 mice and a maximum of ~12 matched anatomical categories, this is
NOT a well-powered correlation test. The headline result reported here is a
simple, honest "how many matched regions agree in direction of effect"
count, with the Pearson/Spearman correlation reported only as a secondary,
clearly-labeled exploratory statistic.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    base_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Compare mouse rabies input strength (CORT vs control) to human ENIGMA effect sizes."
    )
    parser.add_argument(
        "--control-csv",
        type=Path,
        default=Path(r"C:\Users\listo\communal_registration_logcal_drop\rabies_experiment\control\df_tall.csv"),
        help="Path to the control-group rabies df_tall.csv.",
    )
    parser.add_argument(
        "--experimental-csv",
        type=Path,
        default=Path(r"C:\Users\listo\communal_registration_logcal_drop\rabies_experiment\experimental\df_tall.csv"),
        help="Path to the CORT/experimental-group rabies df_tall.csv.",
    )
    parser.add_argument(
        "--enigma-csv",
        type=Path,
        default=base_dir / "enigma_convergence_table.csv",
        help="Path to enigma_convergence_table.csv.",
    )
    parser.add_argument(
        "--channel",
        type=int,
        default=647,
        help="Rabies channel to use (647 = monosynaptic input-labeled cells in the existing pipeline convention).",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=base_dir / "mouse_rabies_vs_enigma_comparison.csv",
        help="Output CSV path for the per-category comparison table.",
    )
    parser.add_argument(
        "--region-manifest-csv",
        type=Path,
        default=base_dir / "mouse_rabies_region_manifest.csv",
        help="Output CSV path listing which fine mouse Allen regions were pooled into each category (for auditing).",
    )
    parser.add_argument(
        "--figure-path",
        type=Path,
        default=base_dir / "figures" / "mouse_rabies_vs_enigma_comparison.png",
        help="Output path for the paired human-vs-mouse effect size comparison figure.",
    )
    parser.add_argument(
        "--value-column",
        type=str,
        default="normalizedcount",
        choices=["normalizedcount", "rawcount"],
        help=(
            "Mouse value column to use. normalizedcount (default) is roughly compositional "
            "(percent of a subject's total channel count, not a strict closed 1.0); rawcount "
            "is provided as a non-compositional sensitivity check."
        ),
    )
    return parser.parse_args()


def cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    """Two-sample Cohen's d, (mean(a) - mean(b)) / pooled_std, matching the
    convention already used by BrainBeam.statistics.BrainBeamStats.CohensD."""

    pooled_std = np.sqrt((np.std(a, ddof=1) ** 2 + np.std(b, ddof=1) ** 2) / 2)
    if pooled_std == 0:
        return np.nan
    return float((np.mean(a) - np.mean(b)) / pooled_std)


# Category -> matcher function over the mouse Allen `regionname` string.
# Every matcher was built by manually inspecting the full 670-region list in
# the actual rabies df_tall.csv files (not guessed), and each documented
# exclusion below is deliberate (see docstring/AGENT_LOG for rationale).
def build_mouse_category_matchers() -> dict[str, "callable"]:
    def is_hippocampus(name: str) -> bool:
        return name == "Hippocampal formation"

    def is_amygdala(name: str) -> bool:
        n = name.lower()
        if "amygdal" not in n:
            return False
        # Exclude white-matter capsule and the ambiguous hippocampal
        # transition zone; keep only amygdalar nuclei/cortex proper.
        if "capsule" in n or "transition area" in n:
            return False
        return True

    def is_acc(name: str) -> bool:
        return name.startswith("Anterior cingulate area")

    def is_ofc(name: str) -> bool:
        return name.startswith("Orbital area")

    def is_insula(name: str) -> bool:
        return name.startswith("Agranular insular area")

    def is_pcc_retrosplenial(name: str) -> bool:
        return name.startswith("Retrosplenial area")

    def is_accumbens(name: str) -> bool:
        return name == "Nucleus accumbens"

    def is_caudate_putamen(name: str) -> bool:
        # Mouse dorsal striatum is not cytoarchitecturally split into
        # caudate vs. putamen; "Caudoputamen" is the standard combined
        # homolog used in the rodent literature. The broader "Striatum" and
        # "Fundus of striatum" labels are distinct voxel sets in this atlas
        # and are deliberately excluded to avoid double counting.
        return name == "Caudoputamen"

    def is_thalamus(name: str) -> bool:
        n = name.lower()
        if "thalamus" not in n:
            return False
        # Exclude the fiber lamina (white matter), not thalamic gray matter.
        if "external medullary lamina" in n:
            return False
        return True

    def is_pallidum(name: str) -> bool:
        n = name.lower()
        return n == "pallidum" or n.startswith("globus pallidus")

    def is_lateral_ventricle(name: str) -> bool:
        return name == "lateral ventricle"

    def is_corpus_callosum(name: str) -> bool:
        # Whole corpus callosum used as the nearest available proxy for the
        # human "tapetum" DTI label; this atlas has no separately labeled
        # tapetum substructure. Hippocampal commissures are excluded because
        # they are anatomically distinct commissural tracts, not part of the
        # corpus callosum proper.
        return name.startswith("corpus callosum") or name == "genu of corpus callosum"

    return {
        "Hippocampus": is_hippocampus,
        "Amygdala": is_amygdala,
        "Anterior cingulate cortex (ACC)": is_acc,
        "Orbitofrontal cortex (OFC)": is_ofc,
        "Insula": is_insula,
        "Posterior cingulate cortex (PCC) / retrosplenial cortex": is_pcc_retrosplenial,
        "Nucleus accumbens": is_accumbens,
        "Caudate + putamen (caudoputamen)": is_caudate_putamen,
        "Thalamus": is_thalamus,
        "Pallidum": is_pallidum,
        "Lateral ventricle": is_lateral_ventricle,
        "Corpus callosum (proxy for tapetum)": is_corpus_callosum,
    }


# Category -> substring(s) used to select matching rows from
# enigma_convergence_table.csv `region` column (case-insensitive).
HUMAN_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Hippocampus": ["hippocampus"],
    "Amygdala": ["amygdala"],
    "Anterior cingulate cortex (ACC)": ["anterior cingulate"],
    "Orbitofrontal cortex (OFC)": ["orbitofrontal"],
    "Insula": ["insular"],
    "Posterior cingulate cortex (PCC) / retrosplenial cortex": ["posterior cingulate"],
    "Nucleus accumbens": ["accumbens"],
    "Caudate + putamen (caudoputamen)": ["caudate", "putamen"],
    "Thalamus": ["thalamus"],
    "Pallidum": ["pallidum"],
    "Lateral ventricle": ["ventricle"],
    "Corpus callosum (proxy for tapetum)": ["tapetum"],
}


def load_mouse_data(args: argparse.Namespace) -> pd.DataFrame:
    """Load and concatenate control + CORT rabies data for the target channel,
    dropping subjects with a failed rabies channel (near-zero total counts
    across the whole brain, indicating a failed injection/registration
    rather than a real biological zero)."""

    control_df = pd.read_csv(args.control_csv)
    experimental_df = pd.read_csv(args.experimental_csv)

    # Both source files use group == 'control' as shipped; the experimental
    # file is the CORT/stress cohort, so its group label is overwritten here
    # (same convention as the existing run_rabies_fostrap_correlation.py).
    experimental_df = experimental_df.copy()
    experimental_df["group"] = "cort"

    df = pd.concat([control_df, experimental_df], ignore_index=True)
    df = df[df["channel"] == args.channel].copy()

    # QC: exclude any subject whose total rawcount for this channel is
    # near zero across the ENTIRE brain (not just one region) -- this
    # indicates a failed rabies injection/registration for that subject,
    # not a genuine biological absence of input. Verified manually: subject
    # 4467196_5 has rawcount==0 in channels 647/488/785 and ~3 total counts
    # (out of ~1340 regions) in channel 561, i.e. no usable signal in any
    # channel, and was silently included (uncorrected) in the first pass of
    # this analysis, biasing every single region's CORT-group mean toward
    # zero. A subject total below this threshold cannot represent real
    # rabies labeling and must be dropped before computing group effects.
    subject_totals = df.groupby("suid")["rawcount"].sum()
    qc_fail_threshold = 10.0
    failed_subjects = subject_totals[subject_totals < qc_fail_threshold].index.tolist()
    if failed_subjects:
        print(
            f"QC: excluding {len(failed_subjects)} subject(s) with near-zero total "
            f"channel-{args.channel} counts (likely failed injection/registration): {failed_subjects}"
        )
        df = df[~df["suid"].isin(failed_subjects)].copy()

    return df


def compute_mouse_category_effects(
    mouse_df: pd.DataFrame, matchers: dict[str, "callable"], value_col: str = "normalizedcount"
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Sum bilateral counts per subject per category, then compute
    control-vs-CORT Cohen's d / t-test per category.

    `value_col` defaults to `normalizedcount` (percent of that subject's
    total channel-647 count, roughly compositional -- summing to ~0.7-0.97
    rather than a strict 1.0 across subjects, per manual inspection). This
    is not a fully closed compositional system, but a region's share can
    still be pulled up or down mechanically by changes in other regions'
    shares rather than by a true independent biological change in that
    region alone. `rawcount` is provided as a non-compositional sensitivity
    check via `--value-column rawcount` on the command line."""

    manifest_rows = []
    result_rows = []

    for category, matcher in matchers.items():
        region_mask = mouse_df["regionname"].apply(matcher)
        matched_regions = sorted(mouse_df.loc[region_mask, "regionname"].unique())
        for region in matched_regions:
            manifest_rows.append({"category": category, "mouse_regionname": region})

        if not matched_regions:
            result_rows.append(
                {
                    "category": category,
                    "n_mouse_subregions_pooled": 0,
                    "control_n": 0,
                    "cort_n": 0,
                    "control_mean": np.nan,
                    "cort_mean": np.nan,
                    "cohens_d_cort_minus_control": np.nan,
                    "t_value": np.nan,
                    "p_value": np.nan,
                }
            )
            continue

        cat_df = mouse_df[region_mask]
        # Sum ipsilateral + contralateral + all pooled subregions per subject
        # to get one bilateral, whole-category value per animal.
        per_subject = cat_df.groupby(["suid", "group"], as_index=False)[value_col].sum()

        control_vals = per_subject.loc[per_subject["group"] == "control", value_col].to_numpy()
        cort_vals = per_subject.loc[per_subject["group"] == "cort", value_col].to_numpy()

        if len(control_vals) < 2 or len(cort_vals) < 2:
            d = np.nan
            t_stat, p_value = np.nan, np.nan
        else:
            d = cohens_d(cort_vals, control_vals)
            t_stat, p_value = stats.ttest_ind(cort_vals, control_vals)

        result_rows.append(
            {
                "category": category,
                "n_mouse_subregions_pooled": len(matched_regions),
                "control_n": len(control_vals),
                "cort_n": len(cort_vals),
                "control_mean": float(np.mean(control_vals)) if len(control_vals) else np.nan,
                "cort_mean": float(np.mean(cort_vals)) if len(cort_vals) else np.nan,
                "cohens_d_cort_minus_control": d,
                "t_value": t_stat,
                "p_value": p_value,
            }
        )

    return pd.DataFrame(result_rows), pd.DataFrame(manifest_rows)


def compute_human_category_effects(enigma_df: pd.DataFrame) -> pd.DataFrame:
    """Average ENIGMA effect sizes per category, kept separate by disorder_group."""

    rows = []
    for category, keywords in HUMAN_CATEGORY_KEYWORDS.items():
        mask = pd.Series(False, index=enigma_df.index)
        for kw in keywords:
            mask = mask | enigma_df["region"].str.contains(kw, case=False, na=False)
        matched = enigma_df.loc[mask]
        for disorder_group, group_df in matched.groupby("disorder_group"):
            rows.append(
                {
                    "category": category,
                    "disorder_group": disorder_group,
                    "n_human_rows": len(group_df),
                    "human_effect_size_mean": group_df["effect_size"].mean(),
                    "human_matched_regions": "; ".join(sorted(group_df["region"].unique())),
                    "human_effect_size_metrics": "; ".join(sorted(group_df["effect_size_metric"].unique())),
                }
            )
    return pd.DataFrame(rows)


def make_comparison_figure(combined_df: pd.DataFrame, output_path: Path) -> None:
    """Paired bar chart of human ENIGMA effect size vs. mouse rabies Cohen's d
    per matched anatomical category, faceted by disorder group."""

    plot_df = combined_df.dropna(subset=["human_effect_size_mean", "cohens_d_cort_minus_control"]).copy()
    if plot_df.empty:
        print("No matched categories with valid data; skipping comparison figure.")
        return

    plot_df = plot_df.sort_values(["disorder_group", "category"])
    sns.set_theme(style="whitegrid")

    disorder_groups = plot_df["disorder_group"].unique()
    fig, axes = plt.subplots(
        1, len(disorder_groups), figsize=(7 * len(disorder_groups), max(4, 0.5 * plot_df["category"].nunique())),
        sharey=False,
    )
    if len(disorder_groups) == 1:
        axes = [axes]

    for ax, disorder_group in zip(axes, disorder_groups):
        sub = plot_df[plot_df["disorder_group"] == disorder_group]
        y_pos = np.arange(len(sub))
        colors = ["#2a9d8f" if agree else "#e76f51" for agree in sub["direction_agreement"]]

        ax.barh(y_pos - 0.2, sub["human_effect_size_mean"], height=0.35, label="Human ENIGMA effect size", color="#264653")
        ax.barh(y_pos + 0.2, sub["cohens_d_cort_minus_control"], height=0.35, label="Mouse rabies Cohen's d (CORT-control)", color=colors)
        ax.axvline(0, color="black", linewidth=0.8)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(sub["category"])
        ax.set_xlabel("Effect size")
        ax.set_title(f"{disorder_group}: green mouse bar = same direction as human, orange = opposite")
        ax.legend(loc="lower right", fontsize=8)

    fig.suptitle(
        "Mouse rabies-input change (CORT vs. control) vs. human ENIGMA structural effect size, by category\n"
        "Qualitative convergence check only \u2014 NOT a validated quantitative correlation (see README caveats)",
        fontsize=11,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300)
    plt.close(fig)
    print(f"Wrote figure: {output_path}")


def main() -> None:
    """Run the mouse-rabies-vs-ENIGMA convergence comparison."""

    args = parse_args()

    mouse_df = load_mouse_data(args)
    matchers = build_mouse_category_matchers()
    mouse_effects_df, manifest_df = compute_mouse_category_effects(mouse_df, matchers, value_col=args.value_column)

    enigma_df = pd.read_csv(args.enigma_csv)
    human_effects_df = compute_human_category_effects(enigma_df)

    combined_df = human_effects_df.merge(mouse_effects_df, on="category", how="left")
    combined_df["direction_agreement"] = np.sign(combined_df["human_effect_size_mean"]) == np.sign(
        combined_df["cohens_d_cort_minus_control"]
    )
    # Note: human effect sizes are disorder-minus-control (smaller in
    # disease = negative). Mouse Cohen's d here is CORT-minus-control, so a
    # matching NEGATIVE mouse d (less rabies input in CORT) lines up with a
    # matching NEGATIVE human d (smaller volume in patients) as "same
    # direction of stress/disease-related change."

    combined_df.to_csv(args.output_csv, index=False)
    manifest_df.to_csv(args.region_manifest_csv, index=False)
    make_comparison_figure(combined_df, args.figure_path)

    print(f"Wrote per-category comparison table to: {args.output_csv}")
    print(f"Wrote mouse region pooling manifest to: {args.region_manifest_csv}")

    valid_df = combined_df.dropna(subset=["human_effect_size_mean", "cohens_d_cort_minus_control"])
    n_matched = len(valid_df)
    n_agree = int(valid_df["direction_agreement"].sum())
    n_categories_tested = mouse_effects_df["category"].nunique()
    bonferroni_alpha = 0.05 / max(n_categories_tested, 1)

    print(f"\n{n_matched} human-vs-mouse ROW comparisons available (category x disorder_group; NOT independent "
          f"tests -- see per-category deduplicated count below).")
    print(f"Direction of effect agrees in {n_agree} / {n_matched} row comparisons "
          f"({100 * n_agree / n_matched:.0f}%, if n_matched > 0).")
    print(f"Bonferroni-corrected alpha for {n_categories_tested} mouse category tests: {bonferroni_alpha:.4f}")
    sig_categories = mouse_effects_df.loc[mouse_effects_df["p_value"] < bonferroni_alpha, "category"].tolist()
    print(f"Mouse categories surviving Bonferroni correction: {sig_categories if sig_categories else 'none'}")

    # IMPORTANT: because the mouse Cohen's d is identical across disorder
    # groups within a category (mouse data has no MDD/PTSD distinction),
    # the row-level count above double-counts categories that appear for
    # both MDD and PTSD -- these are NOT independent comparisons. The
    # deduplicated per-CATEGORY agreement below is the more honest primary
    # statistic, with a category counted as "agree" only if ALL available
    # human rows for it agree in direction with the single mouse value.
    category_level = (
        valid_df.groupby("category")
        .agg(
            all_agree=("direction_agreement", "all"),
            any_disagree=("direction_agreement", lambda s: not s.all() and s.any()),
            n_disorder_rows=("direction_agreement", "size"),
        )
        .reset_index()
    )
    n_cat = len(category_level)
    n_cat_agree = int(category_level["all_agree"].sum())
    n_cat_mixed = int(category_level["any_disagree"].sum())
    print(f"\nDeduplicated per-CATEGORY agreement (the more honest primary statistic): "
          f"{n_cat_agree} / {n_cat} categories fully agree in direction across all available human rows.")
    if n_cat_mixed:
        mixed_cats = category_level.loc[category_level["any_disagree"], "category"].tolist()
        print(f"  {n_cat_mixed} categor(y/ies) had MDD/PTSD disagree with each other on direction "
              f"(near-zero/unstable human effect size, not a meaningful signal): {mixed_cats}")

    binom_result = stats.binomtest(n_cat_agree, n_cat, p=0.5, alternative="two-sided")
    print(f"Binomial test vs. chance (p=0.5): {n_cat_agree}/{n_cat} agree, "
          f"two-sided p={binom_result.pvalue:.3f} (NOT significantly different from chance)"
          if binom_result.pvalue >= 0.05 else
          f"Binomial test vs. chance (p=0.5): {n_cat_agree}/{n_cat} agree, two-sided p={binom_result.pvalue:.3f}")

    for disorder_group, group_df in valid_df.groupby("disorder_group"):
        n = len(group_df)
        n_agree_group = int(group_df["direction_agreement"].sum())
        print(f"  {disorder_group}: {n_agree_group} / {n} categories agree in direction "
              f"({100 * n_agree_group / n:.0f}%)" if n else f"  {disorder_group}: no matched categories")
        if n >= 4:
            r_pearson, p_pearson = stats.pearsonr(
                group_df["human_effect_size_mean"], group_df["cohens_d_cort_minus_control"]
            )
            r_spearman, p_spearman = stats.spearmanr(
                group_df["human_effect_size_mean"], group_df["cohens_d_cort_minus_control"]
            )
            print(
                f"    [EXPLORATORY, low n={n}] Pearson r={r_pearson:.2f} (p={p_pearson:.3f}), "
                f"Spearman rho={r_spearman:.2f} (p={p_spearman:.3f}) -- "
                "not a substitute for the direction-agreement count above given this sample size."
            )
        else:
            print(f"    Too few matched categories (n={n}) for even an exploratory correlation.")

    print(
        "\nCAVEAT: this is a qualitative convergence check, not a validated quantitative "
        "correlation. Mouse n=9 control / 8 CORT; at most 12 anatomically-matched categories; "
        "primate-specific cortical regions (precuneus, STG/MTG, parietal gyri, lingual gyrus) "
        "were deliberately excluded rather than force-matched to a mouse homolog."
    )


if __name__ == "__main__":
    main()
