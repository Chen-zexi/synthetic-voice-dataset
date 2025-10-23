#!/bin/bash
# Helper script to run conversation generation with proper PYTHONPATH
# Usage: ./run_generation.sh --type scam --count 10 --verbose

PYTHONPATH=./doc python3 generate_for_labeling.py "$@"


