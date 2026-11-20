"""Build the Cake Pricing Calculator (blank + SAMPLE).

Usage: python build_workbook.py [OUT_DIR]
"""
import sys
from pathlib import Path

import cake_config
import cake_engine

if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "dist" / "cake-pricing-calculator"
    cake_engine.main(cake_config, out)
