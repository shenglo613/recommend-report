"""Tests for multi-select questionnaire feature."""
from app.services.insurance_engine import InsuranceEngine
from app.models.request import AnalysisQA


def test_engine_initializes():
    """Smoke test: engine initializes with valid inputs."""
    engine = InsuranceEngine(registration_year=2024, displacement=1998)
    assert engine.car_age >= 0
    assert engine.indices["A"] == 3