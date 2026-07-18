#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Thin wrapper around the LinReg CLI (https://github.com/DJESTRIN/LinReg),
vendored as a git submodule at external/LinReg.

LinReg is developed/versioned separately from BrainBeam and is still under
active development, so it is consumed here purely as a CLI subprocess (per
its own CONTRACT.md) rather than imported as a library. This keeps BrainBeam
decoupled from LinReg's internal API while still giving it access to
LinReg's automatic EDA / model-selection / fitting / reporting pipeline.

Setup (one-time):
    git submodule update --init --recursive
    pip install -e external/LinReg/python
    Rscript external/LinReg/R/install_packages.R

Usage:
    from BrainBeam.statistics.linreg_bridge import run_linreg
    run_linreg(input_csv="data.csv", dv="mpg", iv=["hp", "wt"],
               output_dir="out/mpg_analysis")
"""
import shutil
import subprocess
from pathlib import Path
from typing import Iterable, Optional, Union


class LinRegNotFoundError(RuntimeError):
    """Raised when the `linreg` CLI is not installed/importable."""


def _linreg_executable() -> str:
    exe = shutil.which("linreg")
    if exe is None:
        raise LinRegNotFoundError(
            "The 'linreg' CLI was not found on PATH. Install it from the "
            "vendored submodule with:\n"
            "    pip install -e external/LinReg/python"
        )
    return exe


def run_linreg(
    input_csv: Union[str, Path],
    dv: Union[str, Iterable[str]],
    iv: Union[str, Iterable[str]],
    output_dir: Union[str, Path],
    random_effects: Optional[Iterable[str]] = None,
    id_col: Optional[str] = None,
    model_family: str = "auto",
    dry_run: bool = False,
    extra_args: Optional[Iterable[str]] = None,
) -> subprocess.CompletedProcess:
    """Invoke `linreg run` as a subprocess and return the completed process.

    Raises LinRegNotFoundError if the CLI is not installed, and
    subprocess.CalledProcessError if LinReg exits non-zero.
    """
    exe = _linreg_executable()

    def _join(value: Union[str, Iterable[str]]) -> str:
        if isinstance(value, str):
            return value
        return ",".join(value)

    args = [
        exe, "run",
        "--input", str(input_csv),
        "--dv", _join(dv),
        "--iv", _join(iv),
        "--output-dir", str(output_dir),
        "--model-family", model_family,
    ]
    if random_effects:
        args += ["--random-effects", _join(random_effects)]
    if id_col:
        args += ["--id-col", id_col]
    if dry_run:
        args.append("--dry-run")
    if extra_args:
        args += list(extra_args)

    return subprocess.run(args, check=True, capture_output=True, text=True)
