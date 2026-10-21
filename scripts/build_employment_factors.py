"""Regenerate processed employment-factor outputs and audit workbook."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from colombia_employment_factors.mappings import (
    BASE_SOURCE_BY_TECHNOLOGY,
    CAPEX_OPEX_TECH_MAPPINGS,
    DEFAULT_SOURCE_BY_TECHNOLOGY,
    DEFAULT_SOURCE_NOTES,
    RUTOVITZ_2015_CONSTRUCTION_TIME_MAPPINGS,
    RUTOVITZ_2015_CONSTRUCTION_TIME_YEARS,
    RUTOVITZ_2015_RENEWABLE_LOCAL_MANUFACTURING_SHARE,
    RUTOVITZ_2015_RENEWABLE_LOCAL_MANUFACTURING_TECHS,
    RUTOVITZ_DECLINE_FACTORS,
)
from colombia_employment_factors.projections import (
    add_construction_manufacturing_rows,
    project_employment_factors,
)
from colombia_employment_factors.yearly import (
    build_default_model_employment_factors,
    build_yearly_employment_factors,
)
from colombia_employment_factors.adjustments import (
    LEGACY_ROOFTOP_SOURCE, ROOFTOP_SOURCE, apply_productivity_adjustments,
    derive_rooftop, load_policy, retain_published_rooftop, validate_factors,
)
from colombia_employment_factors.jedi import extract_jedi_sources, sha256

RAW_INPUT = ROOT / "data" / "raw" / "employment_factors_input.csv"
TECHNOLOGY_CATALOGUE_SOURCE = ROOT / "docs" / "sources" / "datos_cuantitativos_EN.xlsx"
CAPEX_OPEX_RATIO_INPUT = ROOT / "data" / "audit" / "capex_opex_ratios_2024_2030_2050.csv"
PROCESSED_OUTPUT = ROOT / "data" / "processed" / "employment_factors_with_2030_2050.csv"
YEARLY_OUTPUT = ROOT / "data" / "processed" / "employment_factors_yearly_2024_2055.csv"
MODEL_OUTPUT = ROOT / "data" / "processed" / "employment_factors_model_default_2024_2055.csv"
TECHNOLOGY_ASSUMPTIONS_OUTPUT = ROOT / "data" / "processed" / "technology_assumptions_2024.csv"
AUDIT_OUTPUT = ROOT / "data" / "audit" / "employment_learning_curves_2030_2050.xlsx"
PACKAGE_DATA_OUTPUT = (
    ROOT
    / "src"
    / "colombia_employment_factors"
    / "data"
    / "employment_factors_with_2030_2050.csv"
)
PACKAGE_YEARLY_OUTPUT = (
    ROOT
    / "src"
    / "colombia_employment_factors"
    / "data"
    / "employment_factors_yearly_2024_2055.csv"
)
PACKAGE_MODEL_OUTPUT = (
    ROOT
    / "src"
    / "colombia_employment_factors"
    / "data"
    / "employment_factors_model_default_2024_2055.csv"
)
PACKAGE_TECHNOLOGY_ASSUMPTIONS_OUTPUT = (
    ROOT
    / "src"
    / "colombia_employment_factors"
    / "data"
    / "technology_assumptions_2024.csv"
)


def _as_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _catalogue_rows_by_technology(path: Path) -> dict[str, dict[str, object]]:
    import openpyxl

    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    rows_by_technology = {}
    for worksheet in workbook.worksheets:
        if worksheet.title in {"Guide&Cover", "Index"}:
            continue

        technology_name = worksheet.title.split(". ", 1)[1]
        row_data = {
            "technology_sheet": worksheet.title,
            "lifetime_years": None,
            "lifetime_source_year": None,
            "lifetime_row_number": None,
            "construction_time_years": None,
            "construction_time_source_year": None,
            "construction_time_row_number": None,
        }
        for row_number, row in enumerate(worksheet.iter_rows(values_only=True), start=1):
            label = row[1] if len(row) > 1 else None
            if label == "Technical lifetime (years)":
                value_2024 = _as_float(row[2])
                value_2030 = _as_float(row[3])
                row_data["lifetime_years"] = value_2024 if value_2024 is not None else value_2030
                row_data["lifetime_source_year"] = 2024 if value_2024 is not None else 2030
                row_data["lifetime_row_number"] = row_number
            elif label == "Construction time (years)":
                value_2024 = _as_float(row[2])
                value_2030 = _as_float(row[3])
                row_data["construction_time_years"] = value_2024 if value_2024 is not None else value_2030
                row_data["construction_time_source_year"] = 2024 if value_2024 is not None else 2030
                row_data["construction_time_row_number"] = row_number

        rows_by_technology[technology_name] = row_data
    return rows_by_technology


def build_technology_assumptions(catalogue_path: Path) -> pd.DataFrame:
    """Extract 2024 technology lifetimes and construction times for model technologies."""
    catalogue_rows = _catalogue_rows_by_technology(catalogue_path)
    rows = []
    for technology in DEFAULT_SOURCE_BY_TECHNOLOGY:
        mapped = CAPEX_OPEX_TECH_MAPPINGS.get(technology, ("", "unmapped_constant", ""))
        catalogue_tech, mapping_type, _ = mapped
        catalogue_row = catalogue_rows.get(catalogue_tech, {})
        notes = []
        lifetime_years = catalogue_row.get("lifetime_years")
        lifetime_source_year = catalogue_row.get("lifetime_source_year")
        construction_time_years = catalogue_row.get("construction_time_years")
        construction_time_source_year = catalogue_row.get("construction_time_source_year")
        source = "Colombian Technology Catalogue"

        if lifetime_source_year == 2030:
            notes.append("2024 catalogue lifetime unavailable; 2030 catalogue value used.")
        if construction_time_source_year == 2030:
            notes.append("2024 catalogue construction time unavailable; 2030 catalogue value used.")

        rutovitz_mapping = RUTOVITZ_2015_CONSTRUCTION_TIME_MAPPINGS.get(technology)
        if construction_time_years is None and rutovitz_mapping:
            construction_time_years = RUTOVITZ_2015_CONSTRUCTION_TIME_YEARS[rutovitz_mapping]
            construction_time_source_year = 2015
            source = "Rutovitz 2015 Table 1"
            notes.append("No matching catalogue row; construction time from Rutovitz 2015 Table 1.")

        if technology.startswith("Transmission"):
            notes.append(
                "No matching Technology Catalogue or Rutovitz 2015 Table 1 construction-time row."
            )

        rows.append(
            {
                "Technology": technology,
                "Catalogue_Tech": catalogue_tech,
                "lifetime_years": lifetime_years,
                "lifetime_source_year": lifetime_source_year,
                "construction_time_years": construction_time_years,
                "construction_time_source_year": construction_time_source_year,
                "construction_time_source": source if construction_time_years is not None else "",
                "technology_sheet": catalogue_row.get("technology_sheet", ""),
                "lifetime_row_number": catalogue_row.get("lifetime_row_number"),
                "construction_time_row_number": catalogue_row.get("construction_time_row_number"),
                "mapping_type": mapping_type,
                "notes": " ".join(notes),
            }
        )

    return pd.DataFrame(rows).sort_values("Technology").reset_index(drop=True)


def _rutovitz_mapping_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Technology": technology,
                "Rutovitz_Table9_Tech": values[0],
                "Latin_America_2030_decline_factor": values[1] if values[1] is not None else "-",
                "Applied_multiplier_2015_to_2030": f'=IF(ISNUMBER(C{row_number}),1-C{row_number},"")',
            }
            for row_number, (technology, values) in enumerate(RUTOVITZ_DECLINE_FACTORS.items(), start=2)
        ]
    )


def _catalogue_mapping_table() -> pd.DataFrame:
    rows = []
    for technology, values in CAPEX_OPEX_TECH_MAPPINGS.items():
        mapped_technology, mapping_type, projection_rule = values
        rows.append(
            {
                "Technology": technology,
                "Catalogue_Tech": mapped_technology,
                "Mapping_Type": mapping_type,
                "Projection_Rule": projection_rule,
            }
        )
    return pd.DataFrame(rows)


def _default_source_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Technology": technology,
                "Default_Source": source,
                "Note": DEFAULT_SOURCE_NOTES.get(technology, ""),
            }
            for technology, source in DEFAULT_SOURCE_BY_TECHNOLOGY.items()
        ]
    )


def _add_table_sheet(workbook: Workbook, name: str, data: pd.DataFrame) -> None:
    sheet = workbook.create_sheet(name)
    header_fill = PatternFill("solid", fgColor="0F766E")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")

    for column_number, column_name in enumerate(data.columns, start=1):
        cell = sheet.cell(1, column_number, column_name)
        cell.fill = header_fill
        cell.font = header_font

    for row_number, row in enumerate(data.itertuples(index=False), start=2):
        for column_number, value in enumerate(row, start=1):
            sheet.cell(row_number, column_number, value)

    reference = f"A1:{get_column_letter(sheet.max_column)}{sheet.max_row}"
    table = Table(displayName=name.replace("_", ""), ref=reference)
    table.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium2",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=True,
        showColumnStripes=False,
    )
    sheet.add_table(table)
    sheet.freeze_panes = "A2"


def _add_overview_sheet(workbook: Workbook) -> None:
    sheet = workbook.active
    sheet.title = "Overview"
    header_fill = PatternFill("solid", fgColor="0F766E")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")

    headers = ["Workbook", "Purpose", "Key inputs", "Notes", "Source context"]
    for column_number, header in enumerate(headers, start=2):
        cell = sheet.cell(2, column_number, header)
        cell.fill = header_fill
        cell.font = header_font

    rows = [
        [
            "Overview",
            "Navigation and assumptions",
            "User inputs highlighted yellow",
            "Supports ex-post jobs calculations for OSeMOSYS-Colombia",
            "Technology Catalogue, Rutovitz, and employment factor inputs",
        ],
        [
            "Mappings_Rutovitz",
            "Mapping to Rutovitz Table 9",
            "Latin America 2030 decline factors",
            "Construction, manufacturing, and O&M for Rutovitz 2015 rows",
            "Rutovitz 2015 Table 9",
        ],
        [
            "Mappings_Catalogue",
            "Mapping to Colombian catalogue",
            "CAPEX/OPEX ratio technology names",
            "Direct, proxy, partial, or constant mapping rule",
            "Colombian Technology Catalogue",
        ],
        [
            "Method_2030_2050",
            "Transparent formulas",
            "Yellow cells are key inputs",
            "Includes equations and worked inputs",
            "For audit and adjustment",
        ],
        [
            "Employment_Outputs",
            "Final long-format outputs",
            "All original and projected rows",
            "CSV-equivalent dataset",
            "For direct model use",
        ],
        [
            "Yearly_All_Sources",
            "Interpolated yearly outputs",
            "All eligible sources and factor types",
            "Annual values for 2024-2055",
            "Sparse projection table interpolated by source/technology/factor/job/unit",
        ],
        [
            "Default_Source_Mapping",
            "Model default source choices",
            "One source per technology",
            "Used to select the model-ready table",
            "Repository default assumptions",
        ],
        [
            "Model_Default_2024_2055",
            "Model-ready yearly outputs",
            "Default-source rows only",
            "Use this table for OSeMOSYS-style retrieval",
            "Derived from Yearly_All_Sources and Default_Source_Mapping",
        ],
        [
            "Technology_Assumptions",
            "Technology lifetime and construction time assumptions",
            "2024 catalogue values plus documented fallback rules",
            "Used when annualizing construction-and-manufacturing job-years",
            "Colombian Technology Catalogue and Rutovitz 2015 Table 1",
        ],
    ]
    for row_number, row in enumerate(rows, start=3):
        for column_number, value in enumerate(row, start=2):
            sheet.cell(row_number, column_number, value)


def _add_method_sheet(workbook: Workbook) -> None:
    sheet = workbook.create_sheet("Method_2030_2050")
    header_fill = PatternFill("solid", fgColor="0F766E")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    input_fill = PatternFill("solid", fgColor="FFF59D")

    headers = ["Input type", "Formula", "2030 input", "2050 input", "Example technology", "Comment"]
    for column_number, header in enumerate(headers, start=2):
        cell = sheet.cell(2, column_number, header)
        cell.fill = header_fill
        cell.font = header_font

    rows = [
        [
            "Rutovitz 2015 C/M/O&M",
            "EF_2030 = EF_2015 * (1 - decline_factor_2030)",
            "Latin America Table 9 coefficient",
            "2050/2030 CAPEX or OPEX ratio",
            "Solar PV",
            "2030 uses Rutovitz Table 9; 2050 uses catalogue CAPEX/OPEX transition ratios.",
        ],
        [
            "CAPEX/OPEX ratio",
            "EF_2030 = EF_base * ratio_2030_2024; EF_2050 = EF_2030 * ratio_2050_2030",
            "2030/2024 CAPEX or OPEX ratio",
            "2050/2030 CAPEX or OPEX ratio",
            "Coal power",
            "Used for non-Rutovitz-2015 projection rows mapped to catalogue ratio technologies. For QBIS rows, the 2030/2024 ratio is applied to corrected 2022 base values for simplicity.",
        ],
        [
            "Yearly interpolation",
            "Linear interpolation between known datapoints; EF_2051-2055 = EF_2050",
            "Known points from original/projected rows",
            "No catalogue ratios beyond 2050",
            "All technologies",
            "Rutovitz 2015 values use the 2015 and 2030 points to interpolate 2024-2029.",
        ],
        [
            "Model default source",
            "Filter yearly table by Default_Source_By_Technology",
            "Default source mapping",
            "One source per technology",
            "Offshore wind fixed",
            "QBIS 2023 is used for fixed and floating offshore wind; other source choices are in Default_Source_Mapping.",
        ],
    ]
    for row_number, row in enumerate(rows, start=3):
        for column_number, value in enumerate(row, start=2):
            sheet.cell(row_number, column_number, value)

    for coordinate in ["D3", "E3", "D4", "E4"]:
        sheet[coordinate].fill = input_fill

    sheet["B7"] = "CAPEX/OPEX ratio inputs"
    sheet["B7"].font = Font(name="Calibri", size=11, bold=True)
    ratios = pd.read_csv(CAPEX_OPEX_RATIO_INPUT)
    ratio_inputs = ratios[
        [
            "technology_name",
            "capex_ratio_2030_over_2024",
            "capex_ratio_2050_over_2030",
            "opex_ratio_2030_over_2024",
            "opex_ratio_2050_over_2030",
        ]
    ].rename(
        columns={
            "technology_name": "Catalogue tech",
            "capex_ratio_2030_over_2024": "CAPEX 2030/2024",
            "capex_ratio_2050_over_2030": "CAPEX 2050/2030",
            "opex_ratio_2030_over_2024": "OPEX 2030/2024",
            "opex_ratio_2050_over_2030": "OPEX 2050/2030",
        }
    )
    start_row = 8
    for column_number, column_name in enumerate(ratio_inputs.columns, start=2):
        cell = sheet.cell(start_row, column_number, column_name)
        cell.fill = header_fill
        cell.font = header_font
    for row_number, row in enumerate(ratio_inputs.itertuples(index=False), start=start_row + 1):
        for column_number, value in enumerate(row, start=2):
            sheet.cell(row_number, column_number, value)


def _autofit_columns(workbook: Workbook) -> None:
    for sheet in workbook.worksheets:
        for column_number in range(1, sheet.max_column + 1):
            width = max(
                len(str(sheet.cell(row_number, column_number).value or ""))
                for row_number in range(1, min(sheet.max_row, 80) + 1)
            )
            sheet.column_dimensions[get_column_letter(column_number)].width = min(max(width + 2, 12), 35)


def _formulaize_projection_rows(sheet, output: pd.DataFrame) -> None:
    columns = {name: index + 1 for index, name in enumerate(output.columns)}
    excel_rows = {index: index + 2 for index in output.index}
    base_rows = {}
    ratio_end_row = 8 + len(pd.read_csv(CAPEX_OPEX_RATIO_INPUT))

    for index, row in output.iterrows():
        key = (
            row["Source"],
            row["Technology"],
            row["Factor_Type"],
            row["Job_Type"],
            row["Unit"],
            row["Year"],
        )
        base_rows[key] = excel_rows[index]

    def value_formula(excel_row: int, base_row: int, ratio_formula: str, column_name: str) -> str:
        column_letter = get_column_letter(columns[column_name])
        return f"={column_letter}{base_row}*{ratio_formula}"

    def capex_opex_ratio_formula(excel_row: int, row: pd.Series) -> str:
        mapped_tech_cell = f"{get_column_letter(columns['Mapped_Catalogue_Tech'])}{excel_row}"
        if not row["Mapped_Catalogue_Tech"]:
            return "1"

        is_opex = row["Factor_Type"] == "O&M"
        if row["Base_Year"] in (2022, 2024) and row["Year"] == 2030:
            ratio_column = "E" if is_opex else "C"
        elif row["Base_Year"] == 2030 and row["Year"] == 2050:
            ratio_column = "F" if is_opex else "D"
        else:
            return "1"

        lookup = (
            f"INDEX(Method_2030_2050!${ratio_column}$9:${ratio_column}${ratio_end_row},"
            f"MATCH({mapped_tech_cell},Method_2030_2050!$B$9:$B${ratio_end_row},0))"
        )
        return f"IFERROR(IF(ISNUMBER({lookup}),{lookup},1),1)"

    def manufacturing_share(row: pd.Series) -> float:
        if (
            row["Source"] == "Rutovitz 2015"
            and row["Technology"] in RUTOVITZ_2015_RENEWABLE_LOCAL_MANUFACTURING_TECHS
        ):
            return RUTOVITZ_2015_RENEWABLE_LOCAL_MANUFACTURING_SHARE
        return 1.0

    for index, row in output.iterrows():
        if (
            row["Source"] == "Rutovitz 2015"
            and row["Year"] == 2030
            and row["Factor_Type"] != "Fuel"
            and row["Method_Applied"] == "Rutovitz Table 9 decline to 2030"
        ):
            key = (
                row["Source"],
                row["Technology"],
                row["Factor_Type"],
                row["Job_Type"],
                row["Unit"],
                row["Base_Year"],
            )
            base_row = base_rows[key]
            excel_row = excel_rows[index]
            factor_column = columns["Rutovitz_2030_Factor"]
            factor_cell = f"{get_column_letter(factor_column)}{excel_row}"
            mapped_tech_cell = f"{get_column_letter(columns['Mapped_Rutovitz_Tech'])}{excel_row}"
            sheet.cell(
                excel_row,
                factor_column,
                f"=INDEX(Mappings_Rutovitz!$D$2:$D$14,MATCH({mapped_tech_cell},Mappings_Rutovitz!$B$2:$B$14,0))",
            )

            for column_name in ("Value", "Value_Numeric", "Projected_Value"):
                sheet.cell(excel_row, columns[column_name], value_formula(excel_row, base_row, factor_cell, column_name))
            continue

        if str(row["Method_Applied"]).startswith(("CAPEX/OPEX ratio projection", "Constant projection")):
            key = (
                row["Source"],
                row["Technology"],
                row["Factor_Type"],
                row["Job_Type"],
                row["Unit"],
                row["Base_Year"],
            )
            base_row = base_rows[key]
            excel_row = excel_rows[index]
            ratio_formula = capex_opex_ratio_formula(excel_row, row)
            for column_name in ("Value", "Value_Numeric", "Projected_Value"):
                sheet.cell(
                    excel_row,
                    columns[column_name],
                    value_formula(excel_row, base_row, ratio_formula, column_name),
                )
            continue

        if row["Method_Applied"] == "Derived Construction&Manufacturing":
            excel_row = excel_rows[index]
            construction_key = (
                row["Source"],
                row["Technology"],
                "Construction",
                row["Job_Type"],
                row["Unit"],
                row["Year"],
            )
            manufacturing_key = (
                row["Source"],
                row["Technology"],
                "Manufacturing",
                row["Job_Type"],
                row["Unit"],
                row["Year"],
            )
            if construction_key not in base_rows or manufacturing_key not in base_rows:
                continue
            construction_row = base_rows[construction_key]
            manufacturing_row = base_rows[manufacturing_key]
            share = manufacturing_share(row)
            for column_name in ("Value", "Value_Numeric", "Projected_Value"):
                column_letter = get_column_letter(columns[column_name])
                sheet.cell(
                    excel_row,
                    columns[column_name],
                    f"={column_letter}{construction_row}+{share}*{column_letter}{manufacturing_row}",
                )


def write_audit_workbook(
    output: pd.DataFrame,
    yearly_output: pd.DataFrame,
    model_output: pd.DataFrame,
    technology_assumptions: pd.DataFrame,
    path: Path,
    default_sources: dict | None = None,
    policy: dict | None = None,
    solar_ratios: list | None = None,
) -> None:
    workbook = Workbook()
    _add_overview_sheet(workbook)
    _add_table_sheet(workbook, "Mappings_Rutovitz", _rutovitz_mapping_table())
    _add_table_sheet(workbook, "Mappings_Catalogue", _catalogue_mapping_table())
    _add_method_sheet(workbook)
    _add_table_sheet(workbook, "Employment_Outputs", output)
    _formulaize_projection_rows(workbook["Employment_Outputs"], output)
    _add_table_sheet(workbook, "Yearly_All_Sources", yearly_output)
    _add_table_sheet(workbook, "Default_Source_Mapping", _default_source_table() if default_sources is None else pd.DataFrame([
        {"Technology": technology, "Default_Source": source} for technology, source in default_sources.items()
    ]))
    _add_table_sheet(workbook, "Model_Default_2024_2055", model_output)
    _add_table_sheet(workbook, "Technology_Assumptions", technology_assumptions)
    if policy is not None:
        _add_table_sheet(workbook, "Productivity_Eligibility", pd.DataFrame(policy["productivity_eligibility"]))
        _add_table_sheet(workbook, "Methodology_Assumptions", pd.DataFrame([
            {"assumption": key, "value": json.dumps(value, ensure_ascii=False)}
            for key, value in policy.items() if key != "productivity_eligibility"
        ]))
        _add_table_sheet(workbook, "Solar_Transfer_Ratios", pd.DataFrame(solar_ratios) if solar_ratios else pd.DataFrame([
            {"status": "PENDING: full-precision utility run missing; published rooftop series retained"}
        ]))
    _autofit_columns(workbook)
    workbook.calculation.calcMode = "auto"
    workbook.calculation.fullCalcOnLoad = True
    workbook.calculation.forceFullCalc = True
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=["low", "central", "high"], default="central")
    parser.add_argument("--solar-projection", choices=["catalogue", "constant-relative"], default="catalogue")
    parser.add_argument("--productivity-transfer", choices=["selective", "none"], default="selective", help="Disable only for source-refresh attribution/reference builds")
    parser.add_argument("--output-dir", type=Path, help="Write a review/scenario build here without changing packaged defaults")
    parser.add_argument("--require-solar-ratios", action="store_true", help="Fail rather than retaining the published rooftop fallback")
    args = parser.parse_args()
    policy_path = ROOT / "data/assumptions/employment_methodology.json"
    policy = load_policy(policy_path)
    source = pd.read_csv(RAW_INPUT)
    extracted, source_manifest = extract_jedi_sources(ROOT, policy)
    keys = ["Source", "Technology", "Factor_Type", "Job_Type", "Year"]
    comparison = source.merge(extracted, on=keys, how="right", suffixes=("_curated", "_cached"), validate="one_to_one")
    numeric = pd.to_numeric(comparison["Value_Numeric_curated"], errors="coerce")
    expected = comparison["Value_Numeric_cached"]
    if numeric.isna().any() or ((numeric-expected).abs() > 1e-12 * expected.abs().clip(lower=1)).any():
        raise ValueError("JEDI caches and curated inputs differ; review and run scripts/extract_jedi_factors.py --write")
    baseline_path = ROOT / policy["published_baseline"]
    if sha256(baseline_path) != policy["published_baseline_sha256"]:
        raise ValueError("Frozen baseline checksum mismatch")
    baseline = pd.read_csv(baseline_path)
    solar_available = "settings" in source_manifest["us_utility"]
    solar_ratios = []
    if solar_available:
        source, solar_ratios = derive_rooftop(source)
    elif args.require_solar_ratios or policy["missing_utility_policy"] != "retain_published_baseline" or args.solar_projection == "constant-relative":
        raise ValueError("Full-precision saved utility run required; rounded screenshots cannot supply ratios")
    validate_factors(source[source["Factor_Type"].isin(["Construction", "Manufacturing", "Construction&Manufacturing", "O&M"])])
    capex_opex_ratios = pd.read_csv(CAPEX_OPEX_RATIO_INPUT)
    output = add_construction_manufacturing_rows(project_employment_factors(source, capex_opex_ratios))
    yearly_output = build_yearly_employment_factors(output)
    if args.solar_projection == "constant-relative":
        utility = yearly_output[(yearly_output["Source"] == "I-JEDI") & (yearly_output["Technology"] == "Utility-scale solar PV")]
        lookup = {(r.Factor_Type, r.Job_Type, r.Year): r.Value_Numeric for r in utility.itertuples()}
        ratios = {(r["phase"], r["category"]): r["ratio"] for r in solar_ratios}
        for index, row in yearly_output[yearly_output["Source"] == ROOFTOP_SOURCE].iterrows():
            value = lookup[(row["Factor_Type"], row["Job_Type"], row["Year"])] * ratios[(row["Factor_Type"], row["Job_Type"])]
            for column in ("Value", "Value_Numeric", "Projected_Value"):
                yearly_output.loc[index, column] = value
            yearly_output.loc[index, "Method_Applied"] = "Constant matched US relative ratio × current-year Colombia utility factor"
    regional_sources = {}
    if args.productivity_transfer == "selective":
        yearly_output, regional_sources = apply_productivity_adjustments(yearly_output, policy, args.scenario)
    defaults = dict(BASE_SOURCE_BY_TECHNOLOGY)
    for technology, adjusted_source in regional_sources.items():
        if defaults.get(technology) == adjusted_source.split(" [LATAM")[0]:
            defaults[technology] = adjusted_source
    if solar_available:
        defaults["Rooftop solar PV"] = ROOFTOP_SOURCE
    else:
        yearly_output = retain_published_rooftop(yearly_output, baseline)
        defaults["Rooftop solar PV"] = LEGACY_ROOFTOP_SOURCE
    validate_factors(yearly_output)
    model_output = build_default_model_employment_factors(yearly_output, defaults)
    validate_factors(model_output, model=True)
    if set(defaults) != set(model_output["Technology"]):
        raise ValueError("Missing default employment technology")
    technology_assumptions = build_technology_assumptions(TECHNOLOGY_CATALOGUE_SOURCE)
    default_build = args.output_dir is None and args.scenario == "central" and args.solar_projection == "catalogue" and args.productivity_transfer == "selective"
    destination = args.output_dir or (PROCESSED_OUTPUT.parent if default_build else ROOT / "data/processed/scenarios" / f"{args.scenario}-{args.solar_projection}-{args.productivity_transfer}")
    destination.mkdir(parents=True, exist_ok=True)
    tables = {PROCESSED_OUTPUT.name: output, YEARLY_OUTPUT.name: yearly_output,
              MODEL_OUTPUT.name: model_output, TECHNOLOGY_ASSUMPTIONS_OUTPUT.name: technology_assumptions}
    for name, table in tables.items():
        table.to_csv(destination / name, index=False, float_format="%.12g", lineterminator="\n")
        if default_build:
            shutil.copyfile(destination / name, PACKAGE_DATA_OUTPUT.parent / name)
    input_paths = sorted(set([*ROOT.glob("src/**/*.py"), *ROOT.glob("scripts/*.py"), policy_path,
        RAW_INPUT, CAPEX_OPEX_RATIO_INPUT, TECHNOLOGY_CATALOGUE_SOURCE, baseline_path,
        ROOT / policy["productivity_evidence"], ROOT / "data/audit/productivity_wdi_2023.json",
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
        "solar_projection": args.solar_projection, "solar_transfer_status": "matched ratios" if solar_available else "pending utility run; published rooftop retained",
        "solar_transfer_ready": solar_available, "solar_ratios": solar_ratios, "jedi_sources": source_manifest}
    manifest_path = destination / "employment_factor_provenance.json"
    manifest_path.write_text(json.dumps(provenance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    if default_build:
        shutil.copyfile(manifest_path, PACKAGE_DATA_OUTPUT.parent / manifest_path.name)
    audit_path = AUDIT_OUTPUT if default_build else destination / AUDIT_OUTPUT.name
    write_audit_workbook(output, yearly_output, model_output, technology_assumptions, audit_path, defaults, policy, solar_ratios)
    print(json.dumps({"destination": str(destination), "model_rows": len(model_output),
                      "solar_transfer_status": provenance["solar_transfer_status"], "scenario": args.scenario}))


if __name__ == "__main__":
    main()
