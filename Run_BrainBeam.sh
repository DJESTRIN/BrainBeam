#!/bin/bash
set -e

script_directory="$(cd "$(dirname "$0")" && pwd)"
python "$script_directory/BrainBeam/gui/BrainBeam.py" "$@"
