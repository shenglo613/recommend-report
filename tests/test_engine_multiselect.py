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


def _make_engine(reg_year=2024, displacement=1998):
    """Helper: create engine with default deluxe-package car."""
    return InsuranceEngine(registration_year=reg_year, displacement=displacement)


def test_single_select_passenger_high_medical():
    """Single-element list behaves like old single-select."""
    engine = _make_engine()
    base_c = engine.indices["C"]
    qa = AnalysisQA(passenger_preference=["high_passenger_medical"])
    engine.apply_questionnaire(qa)
    assert engine.indices["C"] == min(base_c + 1, 4)  # C += 1, clamped


def test_single_select_vehicle_basic_repair():
    engine = _make_engine()
    base_e = engine.indices["E"]
    qa = AnalysisQA(vehicle_protection=["basic_repair"])
    engine.apply_questionnaire(qa)
    assert engine.indices["E"] == min(base_e + 2, 5)  # E += 2 (downgrade)


def test_single_select_liability_statutory_minimum():
    engine = _make_engine()
    base_a = engine.indices["A"]
    base_b = engine.indices["B"]
    qa = AnalysisQA(liability_concern=["statutory_minimum"])
    engine.apply_questionnaire(qa)
    assert engine.indices["A"] == max(1, base_a - 1)
    assert engine.indices["B"] == max(1, base_b - 1)


def test_single_select_service_roadside_100km():
    engine = _make_engine()
    qa = AnalysisQA(service_needs=["roadside_assistance_100km"])
    engine.apply_questionnaire(qa)
    assert engine.indices["G"] == 4  # absolute assignment


def test_single_select_budget_safety_first():
    engine = _make_engine()
    snapshot = dict(engine.indices)
    qa = AnalysisQA(budget_profile=["safety_first"])
    engine.apply_questionnaire(qa)
    for k, v in snapshot.items():
        if v > 0:
            if k == "E":
                assert engine.indices[k] <= v  # E reversed: -= 1
            else:
                assert engine.indices[k] >= v  # others: += 1


def test_single_select_budget_saver():
    engine = _make_engine()
    qa = AnalysisQA(budget_profile=["budget_saver"])
    engine.apply_questionnaire(qa)
    for k, v in engine.indices.items():
        if v > 0:
            if k == "E":
                assert v == 4
            else:
                assert v == 1