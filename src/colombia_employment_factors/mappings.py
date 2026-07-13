"""Technology mappings and projection assumptions."""

from __future__ import annotations

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

TECH_CATALOGUE_MAPPINGS = {
    "Solar PV": ("Solar PV", 0.20, "capacity_ratio"),
    "Onshore wind": ("Wind onshore", 0.05, "capacity_ratio"),
    "Offshore wind": ("Wind offshore", 0.15, "capacity_ratio"),
    "Hydro (large)": ("Hydro", 0.01, "capacity_ratio"),
    "Hydro (small)": ("Hydro", 0.01, "capacity_ratio"),
    "Biomass power": ("Bioenergy", 0.05, "capacity_ratio"),
    "Geothermal power": ("Geothermal", 0.05, "capacity_ratio"),
    "Battery storage (grid)": ("Battery storage", 0.10, "capacity_ratio"),
    "Pumped hydro storage": ("Hydro", 0.01, "capacity_ratio"),
    "Coal power": ("Coal", None, "capex_ratio"),
    "Gas CCGT/OCGT": ("Natural Gas", None, "capex_ratio"),
    "Oil and diesel": ("Natural Gas", None, "capex_ratio_proxy"),
    "Nuclear": ("Nuclear (Large Reactor)", None, "capex_ratio"),
    "Solar thermal/CSP": ("CSP", None, "capacity_ratio"),
    "Ocean": ("Ocean", None, "unmapped"),
    "Battery storage (distributed)": ("Battery storage", 0.10, "capacity_ratio"),
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

DEFAULT_SOURCE_BY_TECHNOLOGY = {
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

DEFAULT_SOURCE_NOTES = {
    "Transmission (single circuit)": (
        "Fallback to JEDI-US because the raw table has no Rutovitz 2025 row "
        "for this specific transmission technology."
    ),
}

CAPACITY_RATIOS = {
    2030: {
        "Solar PV": 2.4,
        "Wind onshore": 1.7,
        "Wind offshore": 3.0,
        "Hydro": 1.1,
        "Bioenergy": 1.3,
        "CSP": 2.4,
        "Geothermal": 1.8,
        "Battery storage": 6.5,
    },
    2050: {
        "Solar PV": 6.5,
        "Wind onshore": 2.9,
        "Wind offshore": 8.8,
        "Hydro": 1.4,
        "Bioenergy": 2.2,
        "CSP": 12.3,
        "Geothermal": 4.2,
        "Battery storage": 27.7,
    },
}

# Approximate CAPEX ratios inferred from catalogue datasheets or fallback
# assumptions where values were not available in extracted text.
CAPEX_RATIOS = {
    2030: {
        "Coal": 0.95,
        "Natural Gas": 0.94,
        "Nuclear (Large Reactor)": 0.90,
        "Oil proxy": 0.94,
    },
    2050: {
        "Coal": 0.90,
        "Natural Gas": 0.88,
        "Nuclear (Large Reactor)": 0.85,
        "Oil proxy": 0.88,
    },
}

PROJECTION_YEARS = (2030, 2050)
PROJECTED_FACTOR_TYPES = ("Construction", "Manufacturing", "Construction&Manufacturing")
RUTOVITZ_PROJECTED_FACTOR_TYPES = ("Construction", "Manufacturing", "O&M")
