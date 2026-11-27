"""Build the Owner-Operator Cost Per Mile & Load Profit Calculator (blank + SAMPLE).

Usage: python build_workbook.py [OUT_DIR]
"""
import sys
from pathlib import Path

import truck_config
import truck_engine

if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "dist" / "owner-operator-cost-per-mile"
    truck_engine.main(truck_config, out)
