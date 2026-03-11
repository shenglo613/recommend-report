"""Tests for multi-select questionnaire feature."""
from app.services.insurance_engine import InsuranceEngine
from app.models.request import AnalysisQA


def test_engine_initializes():
    """Smoke test: engine initializes with valid inputs."""
    engine = InsuranceEngine(registration_year=2024, displacement=1998)
    assert engine.car_age >= 0
    assert engine.indices["A"] == 3


def test_analysis_qa_accepts_list():
    """AnalysisQA should accept list of strings for each category."""
    qa = AnalysisQA(
        passenger_preference=["high_passenger_medical", "high_driver_disability"],
        vehicle_protection=["repair_perfectionist"],
        liability_concern=None,
        service_needs=[],
        budget_profile=["safety_first"],
    )
    assert qa.passenger_preference == ["high_passenger_medical", "high_driver_disability"]
    assert qa.vehicle_protection == ["repair_perfectionist"]
    assert qa.liability_concern is None
    assert qa.service_needs == []
    assert qa.budget_profile == ["safety_first"]


def test_analysis_qa_defaults_to_none():
    """All fields default to None when not provided."""
    qa = AnalysisQA()
    assert qa.passenger_preference is None
    assert qa.vehicle_protection is None
    assert qa.liability_concern is None
    assert qa.service_needs is None
    assert qa.budget_profile is None