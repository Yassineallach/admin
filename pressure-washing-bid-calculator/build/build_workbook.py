"""Build the Pressure Washing Bid Calculator (blank + SAMPLE) with the Brass Ledger pricing engine.

Usage: python build_workbook.py [OUT_DIR]
"""
import sys
from pathlib import Path

import pw_config
import pw_engine

if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "dist" / "pressure-washing-bid-calculator"
    pw_engine.main(pw_config, out)
