#!/bin/bash
# Proxyx — jalankan di Linux/Mac:  ./run.sh
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi
.venv/bin/python -m proxyx "$@"
