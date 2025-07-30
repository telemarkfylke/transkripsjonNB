#!/bin/bash

# Set up environment
export PATH="/opt/homebrew/bin:$PATH"
cd "/Users/fuzzbin/Documents/GitHub_TFK/transkripsjonNB"

# Activate virtual environment and run
source .venv/bin/activate
python HuginLokalTranskripsjon.py
