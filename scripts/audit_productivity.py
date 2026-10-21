"""Reproduce a diagnostic from frozen WDI aggregates; never change model policy.

Use --fetch to explicitly refresh the public API snapshot. Default execution is
offline and writes only data/audit/productivity_evidence.json.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data/audit/productivity_wdi_2023.json"
OUTPUT = ROOT / "data/audit/productivity_evidence.json"
INDICATORS = ("SL.GDP.PCAP.EM.KD", "NV.AGR.TOTL.ZS", "SL.AGR.EMPL.ZS")


def fetch_indicator(indicator):
    url = f"https://api.worldbank.org/v2/country/LAC;OED/indicator/{indicator}?date=2023&format=json&per_page=100&source=2"
    with urlopen(url, timeout=60) as response:
        raw = response.read()
    payload = json.loads(raw)
    if not isinstance(payload, list) or len(payload) != 2 or payload[0]["pages"] != 1:
        raise ValueError(f"Unexpected WDI response for {indicator}")
    return {"url": url, "response_sha256": hashlib.sha256(raw).hexdigest(), "response": payload}


def calculate(snapshot):
    observations = {}
    for item in snapshot["series"]:
        for row in item["response"][1]:
            key = (row["countryiso3code"], row["indicator"]["id"])
            value = row["value"]
            if key in observations or row["date"] != "2023" or value is None or not math.isfinite(value):
                raise ValueError(f"Missing, duplicate or invalid 2023 observation: {key}")
            observations[key] = value
    groups = {}
    for group in ("LAC", "OED"):
        productivity, agriculture_gdp, agriculture_jobs = [observations[group, code] for code in INDICATORS]
        if productivity <= 0 or not 0 <= agriculture_gdp < 100 or not 0 <= agriculture_jobs < 100:
            raise ValueError(f"Invalid productivity or shares for {group}")
        correction = (1 - agriculture_gdp / 100) / (1 - agriculture_jobs / 100)
        groups[group] = {
            "gdp_per_worker_2021_ppp": productivity,
            "agriculture_gdp_percent": agriculture_gdp,
            "agriculture_employment_percent": agriculture_jobs,
            "nonag_correction": correction,
            "nonag_productivity_proxy": productivity * correction,
        }
    whole = groups["LAC"]["gdp_per_worker_2021_ppp"] / groups["OED"]["gdp_per_worker_2021_ppp"]
    nonag = groups["LAC"]["nonag_productivity_proxy"] / groups["OED"]["nonag_productivity_proxy"]
    return {
        "observation_year": 2023,
        "groups": groups,
        "whole_economy_ratio": whole,
        "aggregate_nonag_proxy_ratio": nonag,
        "aggregate_nonag_proxy_inverse": 1 / nonag,
        "formula": "P_nonag = P_all * (1 - agriculture_GDP_share) / (1 - agriculture_employment_share); ratio = P_nonag_LAC / P_nonag_OED",
        "aggregation": "Published WDI aggregates, not simple country averages. Membership and underlying country weights are inherited from this WDI release, not independently reconstructed. Indicator coverage/weights can differ; multiplying aggregate shares by PPP productivity is a diagnostic approximation, not a harmonised country-level sector PPP estimate.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true")
    args = parser.parse_args()
    if args.fetch:
        with ThreadPoolExecutor(max_workers=3) as pool:
            series = list(pool.map(fetch_indicator, INDICATORS))
        snapshot = {"retrieved_at_utc": datetime.now(timezone.utc).isoformat(), "series": series}
        # Validate before replacing the preserved snapshot.
        calculate(snapshot)
        SNAPSHOT.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8", newline="\n")
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    policy = json.loads((ROOT / "data/assumptions/employment_methodology.json").read_text(encoding="utf-8"))
    evidence = {
        "schema_version": 1,
        "snapshot_path": SNAPSHOT.relative_to(ROOT).as_posix(),
        "snapshot_sha256": hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest(),
        "retrieved_at_utc": snapshot["retrieved_at_utc"],
        "rutovitz_2015": {
            "source": "docs/sources/Rutovitzetal2015Calculatingglobalenergysectorjobsmethodology.pdf",
            "source_sha256": hashlib.sha256((ROOT / "docs/sources/Rutovitzetal2015Calculatingglobalenergysectorjobsmethodology.pdf").read_bytes()).hexdigest(),
            "table_8_printed_page": 17,
            "latam_nonag_gdp_per_worker_2005_ppp": 55200,
            "oecd_nonag_gdp_per_worker_2005_ppp": 187600,
            "ratio_from_published_levels": 55200 / 187600,
            "inverse_from_published_levels": 187600 / 55200,
            "table_8_displayed_ratio": 0.29,
            "table_6_2015_multiplier": 3.4,
            "status": "Published-table arithmetic verified; original KILM/IEA observations and agricultural adjustment not reconstructed",
        },
        "oecd_leo_2024": {
            "url": "https://www.oecd.org/en/publications/latin-american-economic-outlook-2024_c437947f-en/full-report/overview_b80bea0f.html",
            "figure": 1, "observation_year": 2023, "reported_ratio": 0.33,
            "measure": "Whole-economy productivity per hour; simple averages of 16 LAC economies and 38 OECD members; underlying source The Conference Board (2024)",
            "lac_members": ["Argentina", "Bolivia", "Brazil", "Chile", "Colombia", "Costa Rica", "Dominican Republic", "Ecuador", "Guatemala", "Jamaica", "Mexico", "Paraguay", "Peru", "Trinidad and Tobago", "Uruguay", "Venezuela"],
            "status": "Plausibility comparison only; not non-agricultural per-worker evidence for 0.32",
        },
        "wdi_diagnostic": calculate(snapshot),
        "adopted_ratios": policy["productivity_ratios"],
        "adopted_central_inverse": 1 / policy["productivity_ratios"]["central"],
        "conclusion": "0.32 retained as an explicit user-approved high-level modelling assumption, not an empirically reproduced 2023 non-agricultural estimate. Current WDI diagnostic and OECD per-hour evidence must not be relabelled as its derivation. Revised data do not reconstruct the unknown original chat data vintage.",
    }
    OUTPUT.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(evidence["wdi_diagnostic"], indent=2))


if __name__ == "__main__":
    main()
