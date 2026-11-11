"""Shim: `python -m proxyx` -> `python -m proxyz` (deprecated di v2.1.0)."""
import sys

print("Peringatan: 'python -m proxyx' sudah berganti nama menjadi "
      "'python -m proxyz' (v2.1.0).", file=sys.stderr)

from proxyz.cli import main

main()
