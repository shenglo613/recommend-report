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


def test_multi_select_opposing_cancel_out():
    """Scenario 1 from spec: +1 and -2 stack to net -1."""
    engine = _make_engine()
    base_c = engine.indices["C"]
    qa = AnalysisQA(passenger_preference=["high_passenger_medical", "basic_passenger"])
    engine.apply_questionnaire(qa)
    # C += 1, then C -= 2 → net -1, then finalize clamps
    expected = max(1, min(4, base_c - 1))
    assert engine.indices["C"] == expected


def test_multi_select_absolute_independent_of_relative():
    """Scenario 2 from spec: relative on E, absolute on F."""
    engine = _make_engine()
    base_e = engine.indices["E"]
    qa = AnalysisQA(vehicle_protection=["repair_perfectionist", "waive_subrogation"])
    engine.apply_questionnaire(qa)
    assert engine.indices["E"] == max(1, base_e - 1)  # E upgraded
    assert engine.indices["F"] == 3  # F set absolutely


def test_multi_select_budget_conflict():
    """Scenario 3 from spec: budget_saver overrides safety_first."""
    engine = _make_engine()
    qa = AnalysisQA(budget_profile=["safety_first", "budget_saver"])
    engine.apply_questionnaire(qa)
    for k, v in engine.indices.items():
        if v > 0:
            if k == "E":
                assert v == 4
            else:
                assert v == 1


def test_cross_category_interaction():
    """Scenario 4 from spec: vehicle upgrade overwritten by budget_saver."""
    engine = _make_engine()  # deluxe: E=2
    qa = AnalysisQA(
        vehicle_protection=["repair_perfectionist"],  # E -= 1 → E=1
        budget_profile=["budget_saver"],               # all = 1, E = 4
    )
    engine.apply_questionnaire(qa)
    assert engine.indices["E"] == 4  # budget_saver overwrites
    for k, v in engine.indices.items():
        if v > 0 and k != "E":
            assert v == 1


def test_multi_select_all_four_passenger_options():
    """All four passenger options selected: C+1-2=-1, D+1+1=+2."""
    engine = _make_engine()
    base_c = engine.indices["C"]
    base_d = engine.indices["D"]
    qa = AnalysisQA(passenger_preference=[
        "high_passenger_medical",   # C += 1
        "high_driver_disability",   # D += 1
        "basic_passenger",          # C -= 2
        "high_driver_medical",      # D += 1
    ])
    engine.apply_questionnaire(qa)
    expected_c = max(1, min(4, base_c + 1 - 2))
    expected_d = max(1, min(4, base_d + 1 + 1))
    assert engine.indices["C"] == expected_c
    assert engine.indices["D"] == expected_d


def test_multi_select_service_all_absolutes():
    """All absolute options in service_needs."""
    engine = _make_engine()
    qa = AnalysisQA(service_needs=[
        "roadside_assistance_100km",  # G = 4
        "legal_expense",              # I = 3
        "consolation_money",          # J = 3
    ])
    engine.apply_questionnaire(qa)
    assert engine.indices["G"] == 4
    assert engine.indices["I"] == 3
    assert engine.indices["J"] == 3


def test_empty_list_is_noop():
    """Empty list should behave like None (no changes)."""
    engine = _make_engine()
    snapshot = dict(engine.indices)
    qa = AnalysisQA(
        passenger_preference=[],
        vehicle_protection=[],
        liability_concern=[],
        service_needs=[],
        budget_profile=[],
    )
    engine.apply_questionnaire(qa)
    assert engine.indices == snapshot


def test_none_is_noop():
    """None (default) should behave like no answer."""
    engine = _make_engine()
    snapshot = dict(engine.indices)
    qa = AnalysisQA()
    engine.apply_questionnaire(qa)
    assert engine.indices == snapshot


def test_unknown_options_ignored():
    """Unknown option values are silently ignored."""
    engine = _make_engine()
    snapshot = dict(engine.indices)
    qa = AnalysisQA(passenger_preference=["nonexistent_option"])
    engine.apply_questionnaire(qa)
    assert engine.indices == snapshot


def test_budget_noop_options():
    """best_value and ai_balanced are explicit no-ops."""
    engine = _make_engine()
    snapshot = dict(engine.indices)
    qa = AnalysisQA(budget_profile=["best_value", "ai_balanced"])
    engine.apply_questionnaire(qa)
    assert engine.indices == snapshot


def test_persona_tags_multi_select():
    """Multi-select should generate tags for each selected option that has a mapping."""
    engine = _make_engine()
    qa = AnalysisQA(
        passenger_preference=["high_passenger_medical", "high_driver_disability"],
        vehicle_protection=["repair_perfectionist"],
    )
    engine.apply_questionnaire(qa)
    tags = engine.generate_persona_tags(qa)
    assert "重視家人安全" in tags          # high_passenger_medical
    assert "家庭經濟支柱" in tags          # high_driver_disability
    assert "愛車完美主義" in tags          # repair_perfectionist


def test_persona_tags_unmapped_options_skipped():
    """Options without a PERSONA_TAG_MAP entry are silently skipped."""
    engine = _make_engine()
    qa = AnalysisQA(
        passenger_preference=["basic_passenger"],  # not in PERSONA_TAG_MAP
    )
    engine.apply_questionnaire(qa)
    tags = engine.generate_persona_tags(qa)
    # Should have car-age and package tags, but not a tag for basic_passenger
    assert "basic_passenger" not in str(tags)


def test_persona_tags_empty_list():
    """Empty lists produce no questionnaire-based tags."""
    engine = _make_engine()
    qa = AnalysisQA(passenger_preference=[])
    engine.apply_questionnaire(qa)
    tags = engine.generate_persona_tags(qa)
    # Should only have car-age and package tags
    assert len(tags) == 2  # e.g., ["準新車車主", "適合豪華保障"]