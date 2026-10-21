"""Validate or refresh curated JEDI factors from preserved, saved workbook caches."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from colombia_employment_factors.adjustments import load_policy
from colombia_employment_factors.jedi import extract_jedi_sources, refresh_curated_sources


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Refresh selected curated CSV rows and source manifest; original workbooks are never edited")
    args = parser.parse_args()
    policy = load_policy(ROOT / "data/assumptions/employment_methodology.json")
    extracted, manifest = extract_jedi_sources(ROOT, policy)
    path = ROOT / "data/raw/employment_factors_input.csv"
    original = pd.read_csv(path)
    refreshed = refresh_curated_sources(original, extracted)
    if args.write:
        serialized_manifest = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
        refreshed.to_csv(path, index=False, float_format="%.17g", lineterminator="\n")
        (ROOT / "data/audit/jedi_source_manifest.json").write_text(serialized_manifest, encoding="utf-8", newline="\n")
    else:
        keys = ["Source", "Technology", "Factor_Type", "Job_Type", "Year"]
        actual = original.merge(extracted[keys], on=keys, how="inner").sort_values(keys)
        expected = extracted.sort_values(keys)
        if len(actual) != len(expected) or not all(abs(float(a)-float(b)) <= 1e-12 * max(1,abs(float(b))) for a,b in zip(actual["Value_Numeric"], expected["Value_Numeric"])):
            raise ValueError("Curated JEDI rows differ from saved caches; run with --write after reviewing workbook settings")
    print(json.dumps({"rows": len(extracted), "us_utility_available": "settings" in manifest["us_utility"], "wrote_curated_inputs": args.write}))


if __name__ == "__main__":
    main()
