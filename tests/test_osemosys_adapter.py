import pandas as pd
import pytest

from colombia_employment_factors.adapters.osemosys import calculate_capacity_jobs


def test_calculate_capacity_jobs_maps_osemosys_capacity_to_employment():
    capacity = pd.DataFrame(
        [
            {"TECHNOLOGY": "SOLPV", "YEAR": 2030, "NewCapacity": 10.0},
        ]
    )
    factors = pd.DataFrame(
        [
            {
                "Technology": "Solar PV",
                "Year": 2030,
                "Factor_Type": "Construction",
                "Job_Type": "Direct",
                "Source": "Example",
                "Value_Numeric": 5.0,
            }
        ]
    )

    jobs = calculate_capacity_jobs(
        capacity,
        factors,
        technology_mapping={"SOLPV": "Solar PV"},
        factor_type="Construction",
        job_type="Direct",
    )

    assert jobs.loc[0, "Employment"] == pytest.approx(50.0)
    assert jobs.loc[0, "Model_Technology"] == "SOLPV"
