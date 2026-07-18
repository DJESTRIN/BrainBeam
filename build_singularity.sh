#!/bin/bash
# Build a Singularity/Apptainer image (brainbeam.sif) for running BrainBeam on
# an HPC/SLURM cluster, using Singularity.def in this same directory.
#
# Most clusters run Singularity or its drop-in successor Apptainer instead of
# Docker, since Docker requires a root-owned daemon that isn't available to
# regular HPC users. This script builds the equivalent image using whichever
# of the two commands is available.
#
# Usage:
#   bash build_singularity.sh [output.sif]
#
# Run this from a login/build node (or your own workstation) that has
# fakeroot or sudo access enabled for Singularity/Apptainer builds - this is
# usually NOT available on compute nodes reached via `srun`/`sbatch`. Check
# with your cluster admins if `--fakeroot` fails below; some clusters instead
# require building on your own machine and copying the resulting .sif file
# up to the cluster (e.g. via `scp brainbeam.sif user@cluster:/path/`), or
# using a remote build service (`singularity build --remote ...`).

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
def_file="${script_dir}/Singularity.def"
output_sif="${1:-${script_dir}/brainbeam.sif}"

if [ ! -f "$def_file" ]; then
    echo "Error: could not find Singularity.def next to this script ($def_file)" >&2
    exit 1
fi

if command -v apptainer >/dev/null 2>&1; then
    engine=apptainer
elif command -v singularity >/dev/null 2>&1; then
    engine=singularity
else
    echo "Error: neither 'apptainer' nor 'singularity' was found on PATH." >&2
    echo "Load the appropriate module first, e.g.: module load singularity" >&2
    echo "or: module load apptainer" >&2
    exit 1
fi

echo "Using build engine: $engine"
echo "Building $output_sif from $def_file ..."

if "$engine" build --fakeroot "$output_sif" "$def_file"; then
    echo "Build succeeded: $output_sif"
    exit 0
fi

echo
echo "--fakeroot build failed. This is common on clusters where fakeroot" >&2
echo "namespaces are disabled for regular users. Options:" >&2
echo "  1) Ask your cluster admins to enable fakeroot for your account, or" >&2
echo "     run this same command on a node where it is enabled." >&2
echo "  2) Build $output_sif on your own workstation (with sudo, or with" >&2
echo "     fakeroot enabled) and copy the resulting file to the cluster." >&2
echo "  3) Use a remote build service if configured for your account:" >&2
echo "       $engine build --remote $output_sif $def_file" >&2
exit 1
