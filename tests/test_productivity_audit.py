"""Check the evidence calculation without network access or policy changes."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("productivity_audit", ROOT / "scripts/audit_productivity.py")
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def test_nonag_diagnostic_removes_agriculture_from_both_groups():
    # LAC: 100 * .9/.5 = 180; OECD: 200 * .9/.75 = 240.
    rows = []
    for group, values in [("LAC", (100, 10, 50)), ("OED", (200, 10, 25))]:
        for code, value in zip(AUDIT.INDICATORS, values):
            rows.append({"countryiso3code": group, "indicator": {"id": code}, "date": "2023", "value": value})
    result = AUDIT.calculate({"series": [{"response": [{}, rows]}]})
    assert result["whole_economy_ratio"] == .5
    assert result["aggregate_nonag_proxy_ratio"] == pytest.approx(.75)
    rows[0]["value"] = None
    with pytest.raises(ValueError, match="Missing"):
        AUDIT.calculate({"series": [{"response": [{}, rows]}]})


def test_frozen_evidence_reproduces_diagnostic_without_changing_assumption():
    snapshot = json.loads(AUDIT.SNAPSHOT.read_text(encoding="utf-8"))
    evidence = json.loads(AUDIT.OUTPUT.read_text(encoding="utf-8"))
    assert AUDIT.calculate(snapshot) == evidence["wdi_diagnostic"]
    assert evidence["adopted_ratios"] == {"low": .33, "central": .32, "high": .30}
    assert evidence["adopted_central_inverse"] == 3.125
