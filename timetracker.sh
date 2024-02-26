#!/bin/bash

SCRIPT_NAME="/Users/atash/projects/timetracker/timetracker.py"

# Define the path to your conda environment's activate script
CONDA_ACTIVATE="/opt/homebrew/Caskroom/miniconda/base/bin/activate"

# Check if the activate script exists
if [ ! -f "$CONDA_ACTIVATE" ]; then
    echo "Conda activate script not found. Check the path."
    exit 1
fi

# Activate the conda environment
source "$CONDA_ACTIVATE" scripts
# if arg 1/2 is provided then include it
python3 "$SCRIPT_NAME" ${1:+--timeframe "$1"} ${2:+--period "$2"}