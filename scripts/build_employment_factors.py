"""Build canonical employment factors from manual inputs and preserved workbook caches."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from colombia_employment_factors.mappings import BASE_SOURCE_BY_TECHNOLOGY, CAPEX_OPEX_TECH_MAPPINGS, RUTOVITZ_DECLINE_FACTORS
from colombia_employment_factors.catalogue import read_catalogue
from colombia_employment_factors.projections import add_construction_manufacturing_rows, project_employment_factors
from colombia_employment_factors.yearly import build_default_model_employment_factors, build_yearly_employment_factors
from colombia_employment_factors.adjustments import (
    LEGACY_ROOFTOP_SOURCE, SOLAR_RATIO_SOURCES, apply_productivity_adjustments,
    derive_rooftop, load_policy, retain_published_rooftop, validate_factors,
)
from colombia_employment_factors.jedi import combine_curated_sources, extract_jedi_sources, sha256
from colombia_employment_factors.employment_factors import PRODUCTIVITY_MODEL_FILE

RAW_INPUT = ROOT / "data/curated/employment_factors_input.csv"
CATALOGUE_SELECTIONS = ROOT / "data/curated/catalogue_rows.csv"
TECHNOLOGY_CATALOGUE_SOURCE = ROOT / "docs/sources/datos_cuantitativos_EN.xlsx"
PACKAGE_DATA = ROOT / "src/colombia_employment_factors/data"
SPARSE_FILE = "employment_factors_with_2030_2050.csv"
YEARLY_FILE = "employment_factors_yearly_2024_2055.csv"
MODEL_FILE = "employment_factors_model_default_2024_2055.csv"
ASSUMPTIONS_FILE = "technology_assumptions_2024.csv"


def write_audit_workbook(model, assumptions, ratios, provenance, policy, path):
    """Export a review snapshot; all computations remain in Python."""
    methods = {
        "usage": "Values-only snapshot. Rebuild with Python after changing curated inputs or policy.",
        "methodology": "docs/methodology.md",
        "rutovitz_declines": RUTOVITZ_DECLINE_FACTORS,
        "catalogue_mappings": CAPEX_OPEX_TECH_MAPPINGS,
        "catalogue_ratios": ratios.astype(object).where(pd.notna(ratios), None).to_dict("records"),
        "policy": policy,
        "provenance": provenance,
    }
    # One record per item keeps the evidence readable and below Excel's cell limit.
    records = []
    for section, value in methods.items():
        items = value.items() if isinstance(value, dict) else enumerate(value) if isinstance(value, list) else [("description", value)]
        for key, item in items:
            records.append({"Section": section, "Item": str(key), "Details": json.dumps(item, ensure_ascii=False)})
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for name, table in [("Model_Default_2024_2055", model), ("Technology_Assumptions", assumptions), ("Methods_Provenance", pd.DataFrame(records))]:
            table.to_excel(writer, sheet_name=name, index=False, freeze_panes=(1, 0))
            writer.sheets[name].auto_filter.ref = writer.sheets[name].dimensions


def main() -> None:
    policy_path = ROOT / "data/assumptions/employment_methodology.json"
    policy = load_policy(policy_path)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=["low", "central", "high"], default="central")
    parser.add_argument("--solar-projection", choices=["catalogue", "constant-relative"], default=policy["solar_projection"])
    parser.add_argument("--solar-ratio-method", choices=list(SOLAR_RATIO_SOURCES), default=policy["solar_ratio_method"], help="Rutovitz direct ratios by default; US-JEDI retained for indirect/induced and optional comparison")
    parser.add_argument("--productivity-transfer", choices=["selective", "none"], default="none", help="No transfer by default; selective exports an adjusted sensitivity scenario")
    parser.add_argument("--output-dir", type=Path, help="Write a review/scenario build here without changing packaged defaults")
    parser.add_argument("--require-solar-ratios", action="store_true", help="Fail rather than retaining the published rooftop fallback")
    parser.add_argument("--all-tables", action="store_true", help="Include sparse, all-source and assumption CSVs in a scenario export")
    parser.add_argument("--audit-workbook", action="store_true", help="Also export a values-only three-sheet review workbook")
    args = parser.parse_args()
    central = args.scenario == "central" and args.solar_projection == "catalogue" and args.productivity_transfer == "none" and args.solar_ratio_method == policy["solar_ratio_method"]
    rooftop_source = SOLAR_RATIO_SOURCES[args.solar_ratio_method]
    extracted, source_manifest = extract_jedi_sources(ROOT, policy)
    source = combine_curated_sources(pd.read_csv(RAW_INPUT), extracted)
    baseline_path = ROOT / policy["published_baseline"]
    if sha256(baseline_path) != policy["published_baseline_sha256"]:
        raise ValueError("Frozen baseline checksum mismatch")
    baseline = pd.read_csv(baseline_path)
    solar_available = "settings" in source_manifest["us_utility"]
    solar_ratios = []
    if solar_available:
        source, solar_ratios = derive_rooftop(source, args.solar_ratio_method)
    elif args.require_solar_ratios or policy["missing_utility_policy"] != "retain_published_baseline" or args.solar_projection == "constant-relative":
        raise ValueError("Full-precision saved utility run required; rounded screenshots cannot supply ratios")
    validate_factors(source[source["Factor_Type"].isin(["Construction", "Manufacturing", "Construction&Manufacturing", "O&M"])])
    capex_opex_ratios, technology_assumptions = read_catalogue(TECHNOLOGY_CATALOGUE_SOURCE, CATALOGUE_SELECTIONS)
    output = add_construction_manufacturing_rows(project_employment_factors(source, capex_opex_ratios))
    yearly_output = build_yearly_employment_factors(output)
    if args.solar_projection == "constant-relative":
        utility = yearly_output[(yearly_output["Source"] == "I-JEDI") & (yearly_output["Technology"] == "Utility-scale solar PV")]
        lookup = {(r.Factor_Type, r.Job_Type, r.Year): r.Value_Numeric for r in utility.itertuples()}
        ratios = {(r["phase"], r["category"]): r["ratio"] for r in solar_ratios}
        for index, row in yearly_output[yearly_output["Source"] == rooftop_source].iterrows():
            value = lookup[(row["Factor_Type"], row["Job_Type"], row["Year"])] * ratios[(row["Factor_Type"], row["Job_Type"])]
            for column in ("Value", "Value_Numeric", "Projected_Value"):
                yearly_output.loc[index, column] = value
            yearly_output.loc[index, "Method_Applied"] = "Constant selected relative ratio times current-year Colombia utility factor"
    regional_sources = {}
    if central or args.productivity_transfer == "selective":
        yearly_output, regional_sources = apply_productivity_adjustments(yearly_output, policy, args.scenario)
    defaults = dict(BASE_SOURCE_BY_TECHNOLOGY)
    if solar_available:
        defaults["Rooftop solar PV"] = rooftop_source
    else:
        yearly_output = retain_published_rooftop(yearly_output, baseline)
        defaults["Rooftop solar PV"] = LEGACY_ROOFTOP_SOURCE
    adjusted_defaults = dict(defaults)
    for technology, adjusted_source in regional_sources.items():
        if defaults.get(technology) == adjusted_source.split(" [LATAM")[0]:
            adjusted_defaults[technology] = adjusted_source
    if args.productivity_transfer == "selective":
        defaults = adjusted_defaults
    validate_factors(yearly_output)
    model_output = build_default_model_employment_factors(yearly_output, defaults)
    validate_factors(model_output, model=True)
    if set(defaults) != set(model_output["Technology"]):
        raise ValueError("Missing default employment technology")
    default_build = args.output_dir is None and central
    scenario_name = f"{args.scenario}-{args.solar_projection}-{args.productivity_transfer}"
    if args.solar_ratio_method != policy["solar_ratio_method"]:
        scenario_name += f"-{args.solar_ratio_method}"
    destination = args.output_dir or (PACKAGE_DATA if central else ROOT / "data/processed/scenarios" / scenario_name)
    destination.mkdir(parents=True, exist_ok=True)
    tables = {MODEL_FILE: model_output}
    if central or args.all_tables:
        tables = {SPARSE_FILE: output, YEARLY_FILE: yearly_output, MODEL_FILE: model_output, ASSUMPTIONS_FILE: technology_assumptions}
    if central:
        adjusted_model = build_default_model_employment_factors(yearly_output, adjusted_defaults)
        validate_factors(adjusted_model, model=True)
        tables[PRODUCTIVITY_MODEL_FILE] = adjusted_model
    for name, table in tables.items():
        table.to_csv(destination / name, index=False, float_format="%.12g", lineterminator="\n")
    if default_build:
        capex_opex_ratios.to_csv(ROOT / "data/audit/capex_opex_ratios_2024_2030_2050.csv", index=False, float_format="%.17g", lineterminator="\n")
    input_paths = sorted(set([*ROOT.glob("src/**/*.py"), *ROOT.glob("scripts/*.py"), policy_path,
        RAW_INPUT, CATALOGUE_SELECTIONS, TECHNOLOGY_CATALOGUE_SOURCE, baseline_path,
        ROOT / policy["productivity_evidence"], ROOT / "data/audit/productivity_wdi_2023.json",
        ROOT / policy["solar_ratio_reference"],
        *[ROOT / p for p in policy["jedi_workbooks"].values() if (ROOT / p).exists()]]))
    input_hashes = {p.relative_to(ROOT).as_posix(): sha256(p) for p in input_paths}
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    provenance = {"schema_version": 1, "source_repository": "https://github.com/DEA-GE/colombia-employment-factors",
        "source_revision": revision, "source_tree_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)),
        "input_sha256": input_hashes, "source_content_sha256": hashlib.sha256(json.dumps(input_hashes, sort_keys=True).encode()).hexdigest(),
        "output_sha256": {name: sha256(destination / name) for name in tables},
        "scenario": args.scenario, "productivity_ratio": policy["productivity_ratios"][args.scenario] if args.productivity_transfer == "selective" else 1.0,
        "employment_multiplier": 1 / policy["productivity_ratios"][args.scenario] if args.productivity_transfer == "selective" else 1.0,
        "productivity_transfer": args.productivity_transfer,
        "productivity_status": policy["productivity_status"],
        "productivity_evidence": policy["productivity_evidence"],
        "solar_projection": args.solar_projection, "solar_ratio_method": args.solar_ratio_method,
        "solar_transfer_status": f"matched ratios ({args.solar_ratio_method})" if solar_available else "pending utility run; published rooftop retained",
        "default_sources": defaults, "solar_transfer_ready": solar_available, "solar_ratios": solar_ratios, "jedi_sources": source_manifest}
    if central:
        provenance["optional_productivity_model"] = {
            "file": PRODUCTIVITY_MODEL_FILE, "productivity_transfer": "selective",
            "productivity_ratio": policy["productivity_ratios"]["central"],
            "employment_multiplier": 1 / policy["productivity_ratios"]["central"],
            "default_sources": adjusted_defaults,
        }
    manifest_path = destination / "employment_factor_provenance.json"
    manifest_path.write_text(json.dumps(provenance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    if args.audit_workbook:
        audit_path = (ROOT / "data/audit" if default_build else destination) / "employment_factor_audit.xlsx"
        write_audit_workbook(model_output, technology_assumptions, capex_opex_ratios,
                             provenance, policy, audit_path)
    print(json.dumps({"destination": str(destination), "model_rows": len(model_output),
                      "solar_transfer_status": provenance["solar_transfer_status"], "scenario": args.scenario}))


if __name__ == "__main__":
    main()
