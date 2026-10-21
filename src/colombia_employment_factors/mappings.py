"""Technology mappings and projection assumptions."""

from __future__ import annotations

import json
from importlib import resources

RUTOVITZ_DECLINE_FACTORS = {
    "Coal power": ("Coal", 0.0),
    "Gas CCGT/OCGT": ("Gas", 0.05),
    "Oil and diesel": ("Oil", 0.06),
    "Nuclear": ("Nuclear", 0.0),
    "Biomass power": ("Biomass", 0.03),
    "Hydro (large)": ("Hydro-large", -0.07),
    "Hydro (small)": ("Hydro-small", -0.07),
    "Onshore wind": ("Wind onshore", 0.05),
    "Offshore wind (fixed)": ("Wind offshore", 0.23),
    "Utility-scale solar PV": ("PV", 0.41),
    "Solar thermal (CSP)": ("Solar thermal power", 0.12),
    "Geothermal": ("Geothermal power", 0.48),
    "Ocean": ("Ocean", 0.31),
}

RUTOVITZ_2015_RENEWABLE_LOCAL_MANUFACTURING_SHARE = 0.50
RUTOVITZ_2015_RENEWABLE_LOCAL_MANUFACTURING_TECHS = {
    "Geothermal",
    "Ocean",
    "Offshore wind",
    "Offshore wind (fixed)",
    "Offshore wind (floating)",
    "Onshore wind",
    "Rooftop solar PV",
    "Solar thermal (CSP)",
    "Utility-scale solar PV",
}

CAPEX_OPEX_TECH_MAPPINGS = {
    "Battery storage (distributed)": (
        "Small-scale Lithium-ion",
        "direct",
        "Use CAPEX/OPEX ratios from the mapped Technology Catalogue row.",
    ),
    "Battery storage (grid)": (
        "Utility-scale Lithium-ion",
        "direct",
        "Use CAPEX/OPEX ratios from the mapped Technology Catalogue row.",
    ),
    "Biomass power": (
        "Biomass power plant",
        "direct",
        "Use CAPEX/OPEX ratios from the mapped Technology Catalogue row.",
    ),
    "Coal power": (
        "Coal Supercritical",
        "direct",
        "Use CAPEX/OPEX ratios from the mapped Technology Catalogue row.",
    ),
    "Gas CCGT/OCGT": (
        "CCGT (GAS)",
        "direct",
        "Use CAPEX/OPEX ratios from the mapped Technology Catalogue row.",
    ),
    "Geothermal": (
        "Geothermal large",
        "direct",
        "Use CAPEX/OPEX ratios from the mapped Technology Catalogue row.",
    ),
    "Hydro (large)": (
        "Large Hydro reservoir",
        "direct",
        "Use CAPEX/OPEX ratios from the mapped Technology Catalogue row.",
    ),
    "Hydro (small)": (
        "Small RoR hydro power",
        "direct",
        "Use CAPEX/OPEX ratios from the mapped Technology Catalogue row.",
    ),
    "Nuclear": (
        "Nuclear PWR",
        "direct",
        "Use CAPEX/OPEX ratios from the mapped Technology Catalogue row.",
    ),
    "Offshore wind": (
        "Wind Offshore fixed bottom",
        "direct",
        "Use fixed-bottom offshore wind ratios for generic offshore wind rows.",
    ),
    "Offshore wind (fixed)": (
        "Wind Offshore fixed bottom",
        "direct",
        "Use CAPEX/OPEX ratios from the mapped Technology Catalogue row.",
    ),
    "Offshore wind (floating)": (
        "Wind offshore floating",
        "partial",
        "2024 ratios are unavailable; use 2050/2030 where a 2030 base exists.",
    ),
    "Oil and diesel": (
        "SCGT (GAS)",
        "proxy",
        "Proxy oil/diesel with simple-cycle gas turbine ratios.",
    ),
    "Onshore wind": (
        "Wind Onshore",
        "direct",
        "Use CAPEX/OPEX ratios from the mapped Technology Catalogue row.",
    ),
    "Pumped hydro storage": (
        "Hydro pumped storage",
        "direct",
        "Use CAPEX/OPEX ratios from the mapped Technology Catalogue row.",
    ),
    "Rooftop solar PV": (
        "Residential PV (rooftop)",
        "direct",
        "Use residential rooftop PV ratios for rooftop solar rows.",
    ),
    "Solar thermal (CSP)": (
        "",
        "unmapped_constant",
        "No matching ratio row; hold projected values constant.",
    ),
    "Ocean": (
        "",
        "unmapped_constant",
        "No matching ratio row; hold projected values constant.",
    ),
    "Transmission (double circuit)": (
        "",
        "unmapped_constant",
        "No matching ratio row; hold projected values constant.",
    ),
    "Transmission (other)": (
        "",
        "unmapped_constant",
        "No matching ratio row; hold projected values constant.",
    ),
    "Transmission (single circuit)": (
        "",
        "unmapped_constant",
        "No matching ratio row; hold projected values constant.",
    ),
    "Utility-scale solar PV": (
        "Utility scale PV(tracking)",
        "direct",
        "Use utility-scale tracking PV ratios.",
    ),
}

BASE_SOURCE_BY_TECHNOLOGY = {
    "Battery storage (distributed)": "Rutovitz 2025",
    "Battery storage (grid)": "Rutovitz 2025",
    "Biomass power": "I-JEDI",
    "Coal power": "Rutovitz 2015",
    "Gas CCGT/OCGT": "Rutovitz 2015",
    "Geothermal": "I-JEDI",
    "Hydro (large)": "Rutovitz 2015",
    "Hydro (small)": "Rutovitz 2015",
    "Nuclear": "Rutovitz 2015",
    "Ocean": "Rutovitz 2015",
    "Offshore wind (fixed)": "French QBIS 2023",
    "Offshore wind (floating)": "French QBIS 2023",
    "Oil and diesel": "Rutovitz 2015",
    "Onshore wind": "I-JEDI",
    "Pumped hydro storage": "Rutovitz 2025",
    "Rooftop solar PV": "JEDI-US",
    "Solar thermal (CSP)": "Rutovitz 2015",
    "Transmission (double circuit)": "Rutovitz 2025",
    "Transmission (other)": "Rutovitz 2025",
    "Transmission (single circuit)": "JEDI-US",
    "Utility-scale solar PV": "I-JEDI",
}

def _packaged_default_sources() -> dict[str, str]:
    """Keep the public default selector aligned with the actual packaged table.

    Builders use BASE_SOURCE_BY_TECHNOLOGY before applying the explicit policy;
    readers use resolved source labels recorded in generated provenance.
    """
    path = resources.files("colombia_employment_factors.data").joinpath("employment_factor_provenance.json")
    if not path.is_file():
        return dict(BASE_SOURCE_BY_TECHNOLOGY)
    return json.loads(path.read_text(encoding="utf-8"))["default_sources"]

DEFAULT_SOURCE_BY_TECHNOLOGY = _packaged_default_sources()

DEFAULT_SOURCE_NOTES = {
    "Transmission (single circuit)": (
        "JEDI-US retained as the established default; a Rutovitz 2025 construction row exists "
        "with a different unit and category coverage. Source choice requires separate review."
    ),
}

RUTOVITZ_2015_CONSTRUCTION_TIME_YEARS = {
    "Coal": 5.0,
    "Gas": 2.0,
    "Nuclear": 10.0,
    "Biomass": 2.0,
    "Hydro-large": 2.0,
    "Hydro-small": 2.0,
    "Wind onshore": 2.0,
    "Wind offshore": 4.0,
    "Solar Photovoltaics": 1.0,
    "Geothermal": 2.0,
    "Solar thermal": 2.0,
    "Ocean": 2.0,
}

RUTOVITZ_2015_CONSTRUCTION_TIME_MAPPINGS = {
    "Ocean": "Ocean",
    "Solar thermal (CSP)": "Solar thermal",
}

RUTOVITZ_PROJECTED_FACTOR_TYPES = ("Construction", "Manufacturing", "O&M")


def manufacturing_share(source: str, technology: str) -> float:
    """Existing regional manufacturing share, independent of productivity transfer."""
    if source == "Rutovitz 2015" and technology in RUTOVITZ_2015_RENEWABLE_LOCAL_MANUFACTURING_TECHS:
        return RUTOVITZ_2015_RENEWABLE_LOCAL_MANUFACTURING_SHARE
    return 1.0
