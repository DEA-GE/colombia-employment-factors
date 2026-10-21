"""Explicit rooftop transfers and selective LATAM productivity scenarios.

Original source rows are retained. Productivity is applied after interpolation,
so the recent proxy does not masquerade as a historical source observation.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

from .jedi import JOBS, PHASES
from .mappings import manufacturing_share

ROOFTOP_SOURCE = "I-JEDI Colombia + matched US-JEDI PV ratios"
RUTOVITZ_ROOFTOP_SOURCE = "I-JEDI Colombia + Rutovitz 2025 direct / US-JEDI indirect-induced PV ratios"
SOLAR_RATIO_SOURCES = {"us-jedi": ROOFTOP_SOURCE, "rutovitz-direct": RUTOVITZ_ROOFTOP_SOURCE}
LEGACY_ROOFTOP_SOURCE = "JEDI-US [published baseline; utility run pending]"
PRODUCTIVITY_SUFFIX = " [LATAM productivity proxy]"
FACTOR_KEYS = ["Source", "Technology", "Factor_Type", "Job_Type", "Unit", "Year"]


def load_policy(path: Path) -> dict:
    policy = json.loads(path.read_text(encoding="utf-8"))
    if policy["solar_ratio_method"] not in SOLAR_RATIO_SOURCES:
        raise ValueError("Unsupported solar ratio method")
    for ratio in policy["productivity_ratios"].values():
        if isinstance(ratio, bool) or not math.isfinite(float(ratio)) or not 0 < float(ratio) <= 1:
            raise ValueError("Productivity ratios must be finite and in (0, 1]")
    ratios = policy["productivity_ratios"]
    if not ratios["low"] >= ratios["central"] >= ratios["high"]:
        raise ValueError("Low/central/high employment intensity requires inverse ordering of productivity ratios")
    seen = set()
    for rule in policy["productivity_eligibility"]:
        key = (rule["source"], rule["technology"], rule["phase"])
        if key in seen or rule["phase"] not in ("Construction", "O&M") or not rule.get("evidence"):
            raise ValueError(f"Invalid or duplicate productivity eligibility rule: {key}")
        if rule["source"] not in ("Rutovitz 2015", "Rutovitz 2025", "French QBIS 2023") or rule["technology"] in ("Nuclear", "Biomass power"):
            raise ValueError(f"Ineligible source/technology for productivity transfer: {key}")
        if rule["source"] == "Rutovitz 2015" and (rule["technology"] == "Onshore wind" or (rule["technology"] == "Hydro (large)" and rule["phase"] == "O&M")):
            raise ValueError(f"Already-LATAM factor must not receive an OECD productivity transfer: {key}")
        seen.add(key)
    return policy


def validate_factors(frame: pd.DataFrame, *, model: bool = False) -> None:
    numeric = pd.to_numeric(frame["Value_Numeric"], errors="coerce")
    if numeric.isna().any() or not numeric.map(math.isfinite).all() or (numeric < 0).any():
        raise ValueError("Employment factors must be finite, non-negative numbers")
    years = pd.to_numeric(frame["Year"], errors="coerce")
    if years.isna().any() or not years.map(lambda year: math.isfinite(year) and float(year).is_integer()).all():
        raise ValueError("Employment-factor years must be finite integers")
    keys = [k for k in FACTOR_KEYS if not (model and k == "Source")]
    if frame[keys].isna().any().any() or frame.duplicated(keys).any():
        raise ValueError("Missing or duplicate employment-factor keys")
    if model and frame.duplicated(["Technology", "Factor_Type", "Job_Type", "Year"]).any():
        raise ValueError("Multiple unit/source variants for a model factor")


def derive_rooftop(source: pd.DataFrame, method: str = "us-jedi") -> tuple[pd.DataFrame, list[dict]]:
    """Transfer phase-specific ratios; Rutovitz evidence applies only to Direct.

    The construction-only ratio is explicitly used as a proxy for the combined
    Colombian phase. Manufacturing is neither added to the ratio nor split out.
    """
    if method not in SOLAR_RATIO_SOURCES:
        raise ValueError("Unsupported solar ratio method")
    if source["Source"].isin(SOLAR_RATIO_SOURCES.values()).any():
        raise ValueError("Rooftop transfer already applied")
    rows, audit = [], []
    for phase in PHASES:
        for category in JOBS:
            rutovitz = method == "rutovitz-direct" and category == "Direct"
            ratio_source = "Rutovitz 2025" if rutovitz else "JEDI-US"
            ratio_phase = "Construction" if rutovitz and phase == "Construction&Manufacturing" else phase
            inputs = {}
            for name, src, tech in [("roof", ratio_source, "Rooftop solar PV"), ("utility", ratio_source, "Utility-scale solar PV"), ("anchor", "I-JEDI", "Utility-scale solar PV")]:
                input_phase = phase if name == "anchor" else ratio_phase
                match = source[(source["Source"] == src) & (source["Technology"] == tech)
                    & (source["Factor_Type"] == input_phase) & (source["Job_Type"] == category) & (source["Year"] == 2024)]
                if len(match) != 1:
                    raise ValueError(f"Need one full-precision {name} factor: {src}/{input_phase}/{category}")
                inputs[name] = match.iloc[0]
            if len({r["Unit"] for r in inputs.values()}) != 1:
                raise ValueError("Unmatched units in rooftop transfer")
            roof, utility, anchor = [float(inputs[k]["Value_Numeric"]) for k in ("roof", "utility", "anchor")]
            if not all(math.isfinite(v) and v >= 0 for v in (roof, utility, anchor)) or utility == 0:
                raise ValueError("Invalid rooftop-transfer numerator, denominator or anchor")
            ratio = roof / utility
            row = inputs["anchor"].to_dict()
            row.update(Source=SOLAR_RATIO_SOURCES[method], Technology="Rooftop solar PV", Value=anchor * ratio, Value_Numeric=anchor * ratio)
            rows.append(row)
            audit.append({"phase": phase, "category": category,
                "ratio_source": ratio_source, "ratio_phase": ratio_phase,
                "ratio_rooftop_factor": roof, "ratio_utility_factor": utility,
                "evidence": "Rutovitz et al. (2025), Table 3, p.4; curated 2024 factors" if rutovitz else "Matched saved US-JEDI runs, normalised per MW",
                "boundary_assumption": "Construction-only relative ratio applied to combined I-JEDI direct construction/manufacturing; no manufacturing split" if rutovitz and ratio_phase == "Construction" else "Matched phase; source employment boundaries remain approximate counterparts",
                "ratio": ratio, "colombia_utility_anchor": anchor, "colombia_rooftop": anchor * ratio,
                "unit": row["Unit"], "year": 2024})
    return pd.concat([source, pd.DataFrame(rows)], ignore_index=True), audit


def apply_productivity_adjustments(yearly: pd.DataFrame, policy: dict, scenario: str) -> tuple[pd.DataFrame, dict[str, str]]:
    if yearly["Source"].str.endswith(PRODUCTIVITY_SUFFIX).any():
        raise ValueError("Productivity adjustment already applied")
    multiplier = 1.0 / float(policy["productivity_ratios"][scenario])
    rules = policy["productivity_eligibility"]
    variants, defaults = [], {}
    grouped = {}
    for rule in rules:
        grouped.setdefault((rule["source"], rule["technology"]), []).append(rule["phase"])
    for (source, technology), phases in grouped.items():
        variant = yearly[(yearly["Source"] == source) & (yearly["Technology"] == technology)].copy()
        if variant.empty:
            raise ValueError(f"Productivity rule has no source rows: {source}/{technology}")
        for phase in phases:
            eligible = (variant["Factor_Type"] == phase) & (variant["Job_Type"] == "Direct")
            if not eligible.any():
                raise ValueError(f"Productivity rule has no phase rows: {source}/{technology}/{phase}")
            for col in ("Value", "Value_Numeric", "Projected_Value"):
                variant[col] = pd.to_numeric(variant[col], errors="coerce")
                variant.loc[eligible, col] *= multiplier
        # Retain existing manufacturing localisation once; do not scale global M.
        for _, group in variant.groupby(["Year", "Job_Type"], dropna=False):
            c = group[group["Factor_Type"] == "Construction"]
            m = group[group["Factor_Type"] == "Manufacturing"]
            cm = group[group["Factor_Type"] == "Construction&Manufacturing"]
            if not cm.empty and "Construction" in phases:
                if len(c) != 1 or len(m) != 1 or len(cm) != 1:
                    raise ValueError("Cannot safely recompute combined construction/manufacturing")
                share = manufacturing_share(source, technology)
                value = float(c.iloc[0]["Value_Numeric"]) + share * float(m.iloc[0]["Value_Numeric"])
                for col in ("Value", "Value_Numeric", "Projected_Value"):
                    variant.loc[cm.index, col] = value
        variant["Source"] = source + PRODUCTIVITY_SUFFIX
        variant["Method_Applied"] = variant["Method_Applied"].astype(str) + "; selective LATAM productivity proxy"
        note = f"; fixed regional proxy ratio={1/multiplier:.12g}, inverse={multiplier:.12g}; eligible Direct phases={','.join(phases)}; manufacturing/localisation otherwise unchanged"
        variant["Projection_Input"] = variant["Projection_Input"].fillna("").astype(str) + note
        variants.append(variant)
        defaults[technology] = source + PRODUCTIVITY_SUFFIX
    output = pd.concat([yearly, *variants], ignore_index=True)
    validate_factors(output)
    return output, defaults


def retain_published_rooftop(yearly: pd.DataFrame, baseline: pd.DataFrame) -> pd.DataFrame:
    legacy = baseline[baseline["Technology"] == "Rooftop solar PV"].copy()
    if legacy.empty or len(legacy) != 32 * 6 or set(legacy["Year"]) != set(range(2024, 2056)):
        raise ValueError("Incomplete published rooftop fallback")
    legacy = legacy.drop(columns=["Default_Source", "Default_Source_Note"], errors="ignore")
    legacy["Source"] = LEGACY_ROOFTOP_SOURCE
    legacy["Method_Applied"] = "Published baseline retained pending full-precision US utility run"
    return pd.concat([yearly, legacy], ignore_index=True)
