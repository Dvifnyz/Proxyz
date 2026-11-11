"""Shim: `python -m proxyx` -> `python -m proxyz` (deprecated di v3.0.0)."""
import sys

print("Peringatan: 'python -m proxyx' sudah berganti nama menjadi "
      "'python -m proxyz' (v3.0.0).", file=sys.stderr)

from proxyz.cli import main

main()
