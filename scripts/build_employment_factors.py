"""Regenerate processed employment-factor outputs and audit workbook."""

from __future__ import annotations

import shutil
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
    CAPACITY_RATIOS,
    CAPEX_RATIOS,
    RUTOVITZ_DECLINE_FACTORS,
    TECH_CATALOGUE_MAPPINGS,
)
from colombia_employment_factors.projections import project_employment_factors

RAW_INPUT = ROOT / "data" / "raw" / "employment_factors_final.csv"
PROCESSED_OUTPUT = ROOT / "data" / "processed" / "employment_factors_with_2030_2050.csv"
AUDIT_OUTPUT = ROOT / "data" / "audit" / "employment_learning_curves_2030_2050.xlsx"
PACKAGE_DATA_OUTPUT = (
    ROOT
    / "src"
    / "colombia_employment_factors"
    / "data"
    / "employment_factors_with_2030_2050.csv"
)


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
    for technology, values in TECH_CATALOGUE_MAPPINGS.items():
        mapped_technology, learning_rate, method = values
        rows.append(
            {
                "Technology": technology,
                "Catalogue_Tech": mapped_technology,
                "Learning_rate_or_rule": learning_rate,
                "Method": method,
                "STEPS_ratio_2030": CAPACITY_RATIOS[2030].get(mapped_technology),
                "STEPS_ratio_2050": CAPACITY_RATIOS[2050].get(mapped_technology),
                "CAPEX_ratio_2030": CAPEX_RATIOS[2030].get(mapped_technology),
                "CAPEX_ratio_2050": CAPEX_RATIOS[2050].get(mapped_technology),
            }
        )
    return pd.DataFrame(rows)


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
            "Learning rates and STEPS ratios",
            "Capacity-ratio or CAPEX fallback method",
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
            "EF_2030 = EF_2015 × (1 - decline_factor_2030)",
            "Latin America Table 9 coefficient",
            "n/a",
            "Solar PV",
            "Applied to Construction, Manufacturing, and O&M rows from Rutovitz 2015",
        ],
        [
            "Learning curve",
            "EF_t = EF_2024 * (CapacityRatio_t)^(log2(1-LR))",
            "STEPS accumulated capacity ratio 2030",
            "STEPS accumulated capacity ratio 2050",
            "Onshore wind",
            "Used for Construction, Manufacturing, and Construction&Manufacturing rows",
        ],
        [
            "CAPEX fallback",
            "EF_t = EF_2024 * (CAPEX_t / CAPEX_2024)",
            "2030/2024 CAPEX ratio",
            "2050/2024 CAPEX ratio",
            "Coal power",
            "Used where no catalogue learning-rate/capacity-ratio mapping exists",
        ],
    ]
    for row_number, row in enumerate(rows, start=3):
        for column_number, value in enumerate(row, start=2):
            sheet.cell(row_number, column_number, value)

    for coordinate in ["D3", "D4", "D5", "E4", "E5"]:
        sheet[coordinate].fill = input_fill

    sheet["B8"] = "Key input block"
    sheet["B8"].font = Font(name="Calibri", size=11, bold=True)
    key_inputs = pd.DataFrame(
        [
            ["Solar PV", 0.20, 2.4, 6.5],
            ["Wind onshore", 0.05, 1.7, 2.9],
            ["Wind offshore", 0.15, 3.0, 8.8],
            ["Hydro", 0.01, 1.1, 1.4],
            ["Bioenergy", 0.05, 1.3, 2.2],
            ["Geothermal", 0.05, 1.8, 4.2],
            ["Battery storage", 0.10, 6.5, 27.7],
            ["Coal CAPEX ratio", "", 0.95, 0.90],
            ["Natural Gas CAPEX ratio", "", 0.94, 0.88],
            ["Nuclear CAPEX ratio", "", 0.90, 0.85],
        ],
        columns=["Mapped tech", "Learning rate", "2030 ratio", "2050 ratio"],
    )
    start_row = 9
    for column_number, column_name in enumerate(key_inputs.columns, start=2):
        cell = sheet.cell(start_row, column_number, column_name)
        cell.fill = header_fill
        cell.font = header_font
    for row_number, row in enumerate(key_inputs.itertuples(index=False), start=start_row + 1):
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


def _formulaize_rutovitz_2030_rows(sheet, output: pd.DataFrame) -> None:
    columns = {name: index + 1 for index, name in enumerate(output.columns)}
    excel_rows = {index: index + 2 for index in output.index}
    base_rows = {}

    for index, row in output.iterrows():
        if row["Year"] != row["Base_Year"]:
            continue
        key = (
            row["Source"],
            row["Technology"],
            row["Factor_Type"],
            row["Job_Type"],
            row["Unit"],
            row["Base_Year"],
        )
        base_rows[key] = excel_rows[index]

    for index, row in output.iterrows():
        if (
            row["Source"] != "Rutovitz 2015"
            or row["Year"] != 2030
            or row["Factor_Type"] == "Fuel"
            or row["Method_Applied"] != "Rutovitz Table 9 decline to 2030"
        ):
            continue

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
            column_letter = get_column_letter(columns[column_name])
            sheet.cell(excel_row, columns[column_name], f"={column_letter}{base_row}*{factor_cell}")


def write_audit_workbook(output: pd.DataFrame, path: Path) -> None:
    workbook = Workbook()
    _add_overview_sheet(workbook)
    _add_table_sheet(workbook, "Mappings_Rutovitz", _rutovitz_mapping_table())
    _add_table_sheet(workbook, "Mappings_Catalogue", _catalogue_mapping_table())
    _add_method_sheet(workbook)
    _add_table_sheet(workbook, "Employment_Outputs", output)
    _formulaize_rutovitz_2030_rows(workbook["Employment_Outputs"], output)
    _autofit_columns(workbook)
    workbook.calculation.calcMode = "auto"
    workbook.calculation.fullCalcOnLoad = True
    workbook.calculation.forceFullCalc = True
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)


def main() -> None:
    source = pd.read_csv(RAW_INPUT)
    output = project_employment_factors(source)

    PROCESSED_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(PROCESSED_OUTPUT, index=False, float_format="%.12g")

    PACKAGE_DATA_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(PROCESSED_OUTPUT, PACKAGE_DATA_OUTPUT)

    write_audit_workbook(output, AUDIT_OUTPUT)
    print(
        {
            "csv": str(PROCESSED_OUTPUT),
            "xlsx": str(AUDIT_OUTPUT),
            "rows": len(output),
            "technologies": output["Technology"].nunique(),
        }
    )


if __name__ == "__main__":
    main()
