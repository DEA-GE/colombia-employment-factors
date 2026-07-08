"""Create a PowerPoint methodology deck for the employment factors package.

The script writes a minimal PPTX directly with Office Open XML so it does not
require python-pptx as a dependency.
"""

from __future__ import annotations

import html
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "colombia_employment_factors_methodology.pptx"

EMU_PER_INCH = 914400
SLIDE_W = 13.333333 * EMU_PER_INCH
SLIDE_H = 7.5 * EMU_PER_INCH


def emu(inches: float) -> int:
    return int(inches * EMU_PER_INCH)


def xml_text(text: str) -> str:
    return html.escape(text, quote=True)


def paragraph(text: str, size: int = 2000, bold: bool = False, color: str = "1F2937") -> str:
    b_tag = ' b="1"' if bold else ""
    return (
        "<a:p>"
        "<a:pPr marL=\"0\" marR=\"0\" indent=\"0\"/>"
        f"<a:r><a:rPr lang=\"en-US\" sz=\"{size}\"{b_tag}>"
        f"<a:solidFill><a:srgbClr val=\"{color}\"/></a:solidFill>"
        "</a:rPr>"
        f"<a:t>{xml_text(text)}</a:t>"
        "</a:r>"
        "</a:p>"
    )


def textbox(
    shape_id: int,
    name: str,
    x: float,
    y: float,
    w: float,
    h: float,
    lines: list[str],
    font_size: int = 1900,
    color: str = "1F2937",
    bold_first: bool = False,
    fill: str | None = None,
    line: str | None = None,
) -> str:
    fill_xml = "<a:noFill/>" if fill is None else f"<a:solidFill><a:srgbClr val=\"{fill}\"/></a:solidFill>"
    line_xml = "<a:ln><a:noFill/></a:ln>" if line is None else f"<a:ln><a:solidFill><a:srgbClr val=\"{line}\"/></a:solidFill></a:ln>"
    paragraphs = "".join(
        paragraph(text, size=font_size, bold=bold_first and index == 0, color=color)
        for index, text in enumerate(lines)
    )
    return f"""
    <p:sp>
      <p:nvSpPr>
        <p:cNvPr id="{shape_id}" name="{xml_text(name)}"/>
        <p:cNvSpPr txBox="1"/>
        <p:nvPr/>
      </p:nvSpPr>
      <p:spPr>
        <a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm>
        <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
        {fill_xml}
        {line_xml}
      </p:spPr>
      <p:txBody>
        <a:bodyPr wrap="square" lIns="120000" tIns="90000" rIns="120000" bIns="90000"/>
        <a:lstStyle/>
        {paragraphs}
      </p:txBody>
    </p:sp>
    """


def pill(shape_id: int, x: float, y: float, w: float, text: str, fill: str = "E0F2FE") -> str:
    return textbox(
        shape_id,
        f"Pill {text}",
        x,
        y,
        w,
        0.42,
        [text],
        font_size=1300,
        color="075985",
        bold_first=True,
        fill=fill,
        line="BAE6FD",
    )


def slide_xml(title: str, subtitle: str | None, body_shapes: list[str], slide_no: int) -> str:
    shapes = [
        textbox(2, "Title", 0.55, 0.35, 12.25, 0.72, [title], font_size=2900, color="0F172A", bold_first=True),
    ]
    if subtitle:
        shapes.append(textbox(3, "Subtitle", 0.58, 1.05, 11.9, 0.45, [subtitle], font_size=1450, color="475569"))
    shapes.extend(body_shapes)
    shapes.append(textbox(900, "Footer", 11.8, 7.05, 0.9, 0.25, [str(slide_no)], font_size=900, color="64748B"))
    shapes_xml = "\n".join(shapes)
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:bg><p:bgPr><a:solidFill><a:srgbClr val="F8FAFC"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>
    <p:spTree>
      <p:nvGrpSpPr>
        <p:cNvPr id="1" name=""/>
        <p:cNvGrpSpPr/>
        <p:nvPr/>
      </p:nvGrpSpPr>
      <p:grpSpPr>
        <a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm>
      </p:grpSpPr>
      {shapes_xml}
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>"""


def content_types(slide_count: int) -> str:
    slide_overrides = "\n".join(
        f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        for i in range(1, slide_count + 1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
  {slide_overrides}
</Types>"""


def root_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>"""


def presentation_xml(slide_count: int) -> str:
    slide_ids = "\n".join(
        f'<p:sldId id="{255 + i}" r:id="rId{i}"/>' for i in range(1, slide_count + 1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
                xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:sldIdLst>{slide_ids}</p:sldIdLst>
  <p:sldSz cx="{int(SLIDE_W)}" cy="{int(SLIDE_H)}" type="wide"/>
  <p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>"""


def presentation_rels(slide_count: int) -> str:
    rels = "\n".join(
        f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/>'
        for i in range(1, slide_count + 1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  {rels}
</Relationships>"""


def build_slides() -> list[str]:
    return [
        slide_xml(
            "Colombia Employment Factors",
            "Reusable employment-factor data and learning-curve methodology for power-sector models",
            [
                textbox(10, "Hero", 0.7, 1.75, 7.2, 2.0, [
                    "Purpose",
                    "Separate labour-impact assumptions from the optimization model and expose them as an installable Python package.",
                ], font_size=2100, bold_first=True, fill="E0F2FE", line="7DD3FC"),
                textbox(11, "Stats", 8.35, 1.75, 4.25, 2.0, [
                    "Current dataset",
                    "193 rows",
                    "22 technologies",
                    "Years: 2015, 2024, 2030, 2050",
                ], font_size=1850, bold_first=True, fill="ECFDF5", line="86EFAC"),
                pill(12, 0.7, 4.35, 2.0, "OSeMOSYS"),
                pill(13, 2.95, 4.35, 2.2, "TIMES-MARKAL"),
                pill(14, 5.45, 4.35, 1.4, "LEAP"),
                pill(15, 7.15, 4.35, 2.5, "Ex-post jobs"),
                pill(16, 9.95, 4.35, 2.1, "Just transition"),
            ],
            1,
        ),
        slide_xml(
            "Why A Separate Package?",
            "Employment factors are model-agnostic; model outputs are model-specific.",
            [
                textbox(20, "Reasons", 0.75, 1.65, 5.6, 4.5, [
                    "Separation of concerns",
                    "OSeMOSYS solves the energy system. This package computes labour impacts from the solved capacities.",
                    "Independent versioning",
                    "Employment assumptions can evolve without changing the core model repository.",
                    "Reusable interface",
                    "The same factor table can support OSeMOSYS, TIMES-MARKAL, LEAP, or spreadsheet workflows.",
                ], font_size=1650, bold_first=True),
                textbox(21, "Boundary", 6.8, 1.65, 5.3, 4.5, [
                    "Package boundary",
                    "Inputs: technology, year, capacity, factor filters.",
                    "Outputs: jobs or job-years by source, factor type, and job type.",
                    "Adapters translate model-specific names and columns into this neutral structure.",
                ], font_size=1800, bold_first=True, fill="F1F5F9", line="CBD5E1"),
            ],
            2,
        ),
        slide_xml(
            "Repository Structure",
            "The refactor separates reusable code, source data, generated outputs, and model adapters.",
            [
                textbox(30, "Structure", 0.75, 1.55, 5.9, 4.8, [
                    "src/colombia_employment_factors",
                    "Installable package: formulas, mappings, projections, employment_factors.py, adapters.",
                    "data/raw",
                    "Original curated employment-factor CSV.",
                    "data/processed",
                    "Model-ready long-format employment factors.",
                    "data/audit",
                    "Excel workbook for traceability and review.",
                ], font_size=1550, bold_first=True),
                textbox(31, "Scripts", 7.0, 1.55, 5.1, 4.8, [
                    "scripts/",
                    "Maintainer commands that rebuild outputs from raw inputs.",
                    "tests/",
                    "Formula checks, projection checks, and OSeMOSYS adapter checks.",
                    "docs/sources/",
                    "Source PDFs and catalogue files used for methodology documentation.",
                ], font_size=1650, bold_first=True, fill="F8FAFC", line="CBD5E1"),
            ],
            3,
        ),
        slide_xml(
            "Employment Factor Table",
            "The processed data is long-format so it can be filtered and joined to model outputs.",
            [
                textbox(40, "Schema", 0.75, 1.55, 5.5, 4.8, [
                    "Core dimensions",
                    "Source",
                    "Technology",
                    "Factor_Type",
                    "Job_Type",
                    "Unit",
                    "Year",
                    "Value_Numeric",
                ], font_size=1750, bold_first=True),
                textbox(41, "Metadata", 6.75, 1.55, 5.4, 4.8, [
                    "Projection metadata",
                    "Method_Applied",
                    "Mapped_Rutovitz_Tech",
                    "Rutovitz_2030_Factor",
                    "Mapped_Catalogue_Tech",
                    "Learning_Rate",
                    "Projection_Input",
                    "Base_Year and Projected_Year",
                ], font_size=1700, bold_first=True, fill="EFF6FF", line="93C5FD"),
            ],
            4,
        ),
        slide_xml(
            "Rutovitz 2015 Decline Factors",
            "Construction and manufacturing rows from Rutovitz 2015 are brought to 2030 with Table 9 factors.",
            [
                textbox(50, "Formula", 0.75, 1.65, 6.1, 2.1, [
                    "Formula",
                    "EF_2030 = EF_2015 * (1 + decline_2030)",
                    "The coefficient is technology-specific and uses the Latin America 2030 value from Rutovitz Table 9.",
                ], font_size=1850, bold_first=True, fill="F1F5F9", line="CBD5E1"),
                textbox(51, "Scope", 7.15, 1.65, 4.95, 2.1, [
                    "Scope",
                    "Applied only to Construction and Manufacturing factors.",
                    "O&M and fuel rows remain as original values unless separately updated by source data.",
                ], font_size=1800, bold_first=True, fill="FEF3C7", line="FCD34D"),
                textbox(52, "Examples", 0.75, 4.25, 11.35, 1.35, [
                    "Examples: Coal uses multiplier 0.75; Solar PV uses 1.41; Offshore wind uses 1.23; Hydro large/small use 0.94.",
                ], font_size=1750, fill="FFFFFF", line="CBD5E1"),
            ],
            5,
        ),
        slide_xml(
            "Learning-Curve Method",
            "2024 construction and manufacturing-related rows are projected to 2030 and 2050 using cumulative capacity growth.",
            [
                textbox(60, "Equation", 0.75, 1.6, 11.4, 1.55, [
                    "projected_factor = base_factor * capacity_ratio ^ log2(1 - learning_rate)",
                    "Equivalent spreadsheet exponent: LN(1 - LR) / LN(2)",
                ], font_size=2000, bold_first=True, fill="ECFDF5", line="86EFAC"),
                textbox(61, "Variables", 0.75, 3.55, 5.4, 2.35, [
                    "Variables",
                    "base_factor: 2024 employment factor",
                    "capacity_ratio: accumulated generation capacity relative to 2024",
                    "learning_rate: technology learning rate from the Colombian catalogue mapping",
                ], font_size=1650, bold_first=True),
                textbox(62, "Interpretation", 6.75, 3.55, 5.4, 2.35, [
                    "Interpretation",
                    "As cumulative capacity increases, labour intensity per MW falls for technologies with positive learning rates.",
                    "The approach mirrors the standard cost learning curve, applied to employment intensity.",
                ], font_size=1700, bold_first=True, fill="F8FAFC", line="CBD5E1"),
            ],
            6,
        ),
        slide_xml(
            "Catalogue Mapping And Fallbacks",
            "Technology names are mapped to catalogue categories; missing learning inputs use explicit CAPEX-ratio fallback rules.",
            [
                textbox(70, "Direct mappings", 0.75, 1.55, 5.7, 4.7, [
                    "Direct learning-rate mappings",
                    "Solar PV -> Solar PV",
                    "Onshore wind -> Wind onshore",
                    "Offshore wind -> Wind offshore",
                    "Hydro large/small -> Hydro",
                    "Biomass power -> Bioenergy",
                    "Battery storage -> Battery storage",
                ], font_size=1600, bold_first=True),
                textbox(71, "Fallbacks", 6.85, 1.55, 5.25, 4.7, [
                    "CAPEX-ratio fallback",
                    "EF_t = EF_2024 * (CAPEX_t / CAPEX_2024)",
                    "Used where no catalogue learning-rate/capacity-ratio mapping was available.",
                    "Examples: Coal, Natural Gas, Nuclear, and Oil/Diesel proxy treatment.",
                ], font_size=1700, bold_first=True, fill="FEF2F2", line="FCA5A5"),
            ],
            7,
        ),
        slide_xml(
            "Projection Workflow",
            "The package keeps every projected row auditable through method and mapping metadata.",
            [
                textbox(80, "Step 1", 0.75, 1.65, 3.55, 3.1, [
                    "1. Read base factors",
                    "Load the curated long-format 2015 and 2024 employment-factor table.",
                ], font_size=1700, bold_first=True, fill="EFF6FF", line="93C5FD"),
                textbox(81, "Step 2", 4.75, 1.65, 3.55, 3.1, [
                    "2. Apply method",
                    "Rutovitz Table 9, learning curve, or CAPEX fallback depending on source and technology.",
                ], font_size=1700, bold_first=True, fill="ECFDF5", line="86EFAC"),
                textbox(82, "Step 3", 8.75, 1.65, 3.55, 3.1, [
                    "3. Write outputs",
                    "Generate processed CSV plus audit workbook with mappings and formula context.",
                ], font_size=1700, bold_first=True, fill="F8FAFC", line="CBD5E1"),
                textbox(83, "Output", 0.75, 5.35, 11.55, 0.8, [
                    "Output rows preserve Source, Technology, Factor_Type, Job_Type, Unit, Year, Value_Numeric, and projection metadata.",
                ], font_size=1650),
            ],
            8,
        ),
        slide_xml(
            "OSeMOSYS Integration",
            "The package is designed for ex-post calculations after the OSeMOSYS optimization has solved.",
            [
                textbox(90, "Flow", 0.75, 1.55, 5.5, 4.8, [
                    "Model output",
                    "OSeMOSYS exports technology-year capacity results such as NewCapacity.",
                    "Adapter",
                    "The OSeMOSYS adapter maps model technology names to employment-factor technology names.",
                    "Jobs calculation",
                    "Employment = model_capacity * employment_factor",
                ], font_size=1650, bold_first=True),
                textbox(91, "API", 6.75, 1.55, 5.4, 4.8, [
                    "Python API",
                    "from colombia_employment_factors import get_employment_factors",
                    "from colombia_employment_factors.adapters.osemosys import calculate_capacity_jobs",
                    "factors = get_employment_factors()",
                    "jobs = calculate_capacity_jobs(results, factors)",
                ], font_size=1400, bold_first=True, fill="F1F5F9", line="CBD5E1"),
            ],
            9,
        ),
        slide_xml(
            "Quality And Traceability",
            "The refactor adds repeatability without hiding assumptions.",
            [
                textbox(100, "Quality controls", 0.75, 1.55, 5.7, 4.7, [
                    "Tests",
                    "Learning-curve formula equals the Excel LN expression.",
                    "Projection rows are checked against known values.",
                    "OSeMOSYS adapter merge and multiplication are checked.",
                ], font_size=1750, bold_first=True, fill="ECFDF5", line="86EFAC"),
                textbox(101, "Traceability", 6.85, 1.55, 5.25, 4.7, [
                    "Audit trail",
                    "Generated rows include method, mapped technology, learning rate, and projection input.",
                    "Raw, processed, audit, and source folders have distinct responsibilities.",
                    "Assumptions remain visible for future UPME review.",
                ], font_size=1700, bold_first=True, fill="EFF6FF", line="93C5FD"),
            ],
            10,
        ),
        slide_xml(
            "Recommended Next Steps",
            "The package is ready for GitHub publication and downstream model integration.",
            [
                textbox(110, "Next", 0.75, 1.55, 11.35, 4.9, [
                    "1. Replace approximate CAPEX fallback ratios with fully extracted catalogue values where possible.",
                    "2. Add a documented OSeMOSYS-UPME technology-name mapping file.",
                    "3. Add citation guidance for Rutovitz, the Colombian Technology Catalogue, and derived outputs.",
                    "4. Tag a first release and reference it from OSeMOSYS-UPME requirements.txt.",
                    "5. Add examples for TIMES-MARKAL or other models only through separate adapters.",
                ], font_size=1850, fill="FFFFFF", line="CBD5E1"),
            ],
            11,
        ),
    ]


def create_pptx(path: Path) -> None:
    slides = build_slides()
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as deck:
        deck.writestr("[Content_Types].xml", content_types(len(slides)))
        deck.writestr("_rels/.rels", root_rels())
        deck.writestr("ppt/presentation.xml", presentation_xml(len(slides)))
        deck.writestr("ppt/_rels/presentation.xml.rels", presentation_rels(len(slides)))
        for index, slide in enumerate(slides, start=1):
            deck.writestr(f"ppt/slides/slide{index}.xml", slide)


if __name__ == "__main__":
    create_pptx(OUTPUT)
    print(OUTPUT)
