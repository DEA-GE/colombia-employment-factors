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
    "Offshore wind": ("Wind offshore", 0.23),
    "Utility-scale solar PV": ("PV", 0.41),
    "Solar thermal (CSP)": ("Solar thermal power", 0.12),
    "Geothermal": ("Geothermal power", 0.48),
    "Ocean": ("Ocean", 0.31),
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
