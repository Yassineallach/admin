"""Build the Lawn Care Pricing Calculator (blank + SAMPLE) with the Brass Ledger pricing engine.

Usage: python build_workbook.py [OUT_DIR]
"""
import sys
from pathlib import Path

import engine
import lawn_config

if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "dist" / "lawn-care-pricing-calculator"
    engine.main(lawn_config, out)
