# Multi-Select Questionnaire Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the five questionnaire categories from single-select to multi-select with two-phase (relative-then-absolute) effect stacking.

**Architecture:** Modify `AnalysisQA` model fields from `Optional[str]` to `Optional[List[str]]`. Rewrite `apply_questionnaire()` to iterate over arrays with Phase 1 (relative shifts) then Phase 2 (absolute assignments) per category. Update `generate_persona_tags()` to iterate over arrays.

**Tech Stack:** Python 3.9+, Pydantic v2, FastAPI, pytest (new dev dependency)

**Spec:** `docs/superpowers/specs/2026-03-11-multi-select-questionnaire-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `app/models/request.py` | Modify | Change AnalysisQA field types |
| `app/services/insurance_engine.py` | Modify | Rewrite `apply_questionnaire()`, `generate_persona_tags()` |
| `tests/test_engine_multiselect.py` | Create | All tests for the multi-select feature |
| `requirements.txt` | Modify | Add pytest dev dependency |
| `app/requirements.txt` | No change | Production deps only |

---

## Chunk 1: Setup and Model Change

### Task 1: Add pytest and create test infrastructure

**Files:**
- Modify: `requirements.txt` (add pytest)
- Create: `tests/__init__.py`
- Create: `tests/test_engine_multiselect.py`

- [ ] **Step 1: Add pytest to requirements.txt**

Append `pytest==8.3.5` to the end of `requirements.txt`.

- [ ] **Step 2: Install pytest**

Run: `pip install pytest==8.3.5`
Expected: Successful installation

- [ ] **Step 3: Create test directory and init file**

Create `tests/__init__.py` (empty file).

- [ ] **Step 4: Create test file with a smoke test**

Create `tests/test_engine_multiselect.py`:

```python
"""Tests for multi-select questionnaire feature."""
from app.services.insurance_engine import InsuranceEngine
from app.models.request import AnalysisQA


def test_engine_initializes():
    """Smoke test: engine initializes with valid inputs."""
    engine = InsuranceEngine(registration_year=2024, displacement=1998)
    assert engine.car_age >= 0
    assert engine.indices["A"] == 3
```

- [ ] **Step 5: Run the smoke test**

Run: `cd /Users/shenglo1/robins/recommend-report && python -m pytest tests/test_engine_multiselect.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add requirements.txt tests/
git commit -m "test: add pytest and test infrastructure for multi-select feature"
```

---

### Task 2: Change AnalysisQA model to accept lists

**Files:**
- Modify: `app/models/request.py:25-41`

- [ ] **Step 1: Write a test that sends list values to AnalysisQA**

Add to `tests/test_engine_multiselect.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_engine_multiselect.py::test_analysis_qa_accepts_list -v`
Expected: FAIL (Pydantic validation error — currently expects `str`, not `list`)

- [ ] **Step 3: Update AnalysisQA model**

Modify `app/models/request.py`. Change the import and all five fields:

```python
from typing import Optional, List
from pydantic import BaseModel, Field


# ... (CarDetails and Profile unchanged) ...


class AnalysisQA(BaseModel):
    """五大維度生活化問卷（每類複選，皆為 Optional）"""
    passenger_preference: Optional[List[str]] = Field(
        None, description="車內人安全感: high_passenger_medical|high_driver_disability|basic_passenger|high_driver_medical"
    )
    vehicle_protection: Optional[List[str]] = Field(
        None, description="本車愛護程度: repair_perfectionist|waive_subrogation|theft_protection|basic_repair"
    )
    liability_concern: Optional[List[str]] = Field(
        None, description="車外人責任心: high_excess_liability|high_bodily_injury|statutory_minimum|high_property_damage"
    )
    service_needs: Optional[List[str]] = Field(
        None, description="費用服務應援: roadside_assistance_100km|legal_expense|consolation_money|basic_roadside"
    )
    budget_profile: Optional[List[str]] = Field(
        None, description="預算與性格: safety_first|best_value|budget_saver|ai_balanced"
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_engine_multiselect.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/models/request.py tests/test_engine_multiselect.py
git commit -m "feat: change AnalysisQA fields from single-select to multi-select lists"
```

---

## Chunk 2: Rewrite apply_questionnaire()

### Task 3: Single-selection backward compatibility

**Files:**
- Modify: `app/services/insurance_engine.py:81-142`
- Modify: `tests/test_engine_multiselect.py`

These tests verify that passing a single-element list produces the same result as the old single-select behavior. This ensures no regression.

- [ ] **Step 1: Write backward-compatibility tests**

Add to `tests/test_engine_multiselect.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_engine_multiselect.py -v`
Expected: New tests FAIL (apply_questionnaire expects str attributes, gets list)

- [ ] **Step 3: Rewrite apply_questionnaire() with two-phase logic**

Replace the entire `apply_questionnaire` method in `app/services/insurance_engine.py` (lines 81-142) with:

```python
    def apply_questionnaire(self, qa: AnalysisQA):
        """第二層：問卷位移邏輯（複選版本，兩階段處理）

        Categories processed sequentially 1→5.
        Within each category:
          Phase 1: Apply all relative shifts (+=, -=)
          Phase 2: Apply all absolute assignments (=)
        """

        # --- Category 1: 車內人安全感（affects C, D）---
        for sel in (qa.passenger_preference or []):
            # Phase 1: all are relative
            if sel == "high_passenger_medical":
                self.indices["C"] += 1
            elif sel == "high_driver_disability":
                self.indices["D"] += 1
            elif sel == "basic_passenger":
                self.indices["C"] -= 2
            elif sel == "high_driver_medical":
                self.indices["D"] += 1
        # Phase 2: no absolutes in this category

        # --- Category 2: 本車愛護程度（affects E, F, H）---
        # Phase 1: relative shifts
        for sel in (qa.vehicle_protection or []):
            if sel == "repair_perfectionist":
                self.indices["E"] -= 1
            elif sel == "basic_repair":
                self.indices["E"] += 2
        # Phase 2: absolute assignments
        for sel in (qa.vehicle_protection or []):
            if sel == "waive_subrogation":
                self.indices["F"] = 3
            elif sel == "theft_protection":
                self.indices["H"] = 1

        # --- Category 3: 車外人責任心（affects A, B, K）---
        # Phase 1: relative shifts
        for sel in (qa.liability_concern or []):
            if sel == "high_excess_liability":
                self.indices["B"] += 2
            elif sel == "statutory_minimum":
                self.indices["A"] -= 1
                self.indices["B"] -= 1
            elif sel == "high_property_damage":
                self.indices["A"] += 1
        # Phase 2: absolute assignments
        for sel in (qa.liability_concern or []):
            if sel == "high_bodily_injury":
                self.indices["K"] = 3

        # --- Category 4: 費用服務應援（affects G, I, J）---
        # Phase 1: relative shifts
        for sel in (qa.service_needs or []):
            if sel == "basic_roadside":
                self.indices["G"] -= 1
        # Phase 2: absolute assignments
        for sel in (qa.service_needs or []):
            if sel == "roadside_assistance_100km":
                self.indices["G"] = 4
            elif sel == "legal_expense":
                self.indices["I"] = 3
            elif sel == "consolation_money":
                self.indices["J"] = 3

        # --- Category 5: 全域預算與性格（affects all enabled）---
        # Phase 1: relative shifts
        for sel in (qa.budget_profile or []):
            if sel == "safety_first":
                for k in self.indices:
                    if self.indices[k] > 0:
                        if k == "E":
                            self.indices[k] -= 1
                        else:
                            self.indices[k] += 1
        # Phase 2: absolute assignments
        for sel in (qa.budget_profile or []):
            if sel == "budget_saver":
                for k in self.indices:
                    if self.indices[k] > 0:
                        if k == "E":
                            self.indices[k] = 4
                        else:
                            self.indices[k] = 1

        self.finalize()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_engine_multiselect.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/insurance_engine.py tests/test_engine_multiselect.py
git commit -m "feat: rewrite apply_questionnaire for multi-select with two-phase processing"
```

---

### Task 4: Multi-select stacking and edge cases

**Files:**
- Modify: `tests/test_engine_multiselect.py`

- [ ] **Step 1: Write multi-select stacking tests**

Add to `tests/test_engine_multiselect.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `python -m pytest tests/test_engine_multiselect.py -v`
Expected: All tests PASS (implementation from Task 3 should handle these correctly)

- [ ] **Step 3: Commit**

```bash
git add tests/test_engine_multiselect.py
git commit -m "test: add multi-select stacking and edge case tests"
```

---

## Chunk 3: Update generate_persona_tags and final verification

### Task 5: Update generate_persona_tags() for multi-select

**Files:**
- Modify: `app/services/insurance_engine.py` — locate the `generate_persona_tags` method (note: line numbers will have shifted after Task 3's edits)
- Modify: `tests/test_engine_multiselect.py`

- [ ] **Step 1: Write tests for persona tags with multi-select**

Add to `tests/test_engine_multiselect.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_engine_multiselect.py::test_persona_tags_multi_select -v`
Expected: FAIL (generate_persona_tags still iterates over string values, not lists)

- [ ] **Step 3: Update generate_persona_tags()**

In `app/services/insurance_engine.py`, locate the questionnaire tag section inside `generate_persona_tags()` and replace it:

Current code:
```python
        # 問卷特徵標籤
        if qa:
            for field_val in [
                qa.passenger_preference, qa.vehicle_protection,
                qa.liability_concern, qa.service_needs, qa.budget_profile,
            ]:
                if field_val and field_val in PERSONA_TAG_MAP:
                    tags.append(PERSONA_TAG_MAP[field_val])
```

Replace with:
```python
        # 問卷特徵標籤（複選：遍歷每個類別的陣列）
        if qa:
            for field_vals in [
                qa.passenger_preference, qa.vehicle_protection,
                qa.liability_concern, qa.service_needs, qa.budget_profile,
            ]:
                for val in (field_vals or []):
                    if val in PERSONA_TAG_MAP:
                        tags.append(PERSONA_TAG_MAP[val])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_engine_multiselect.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/insurance_engine.py tests/test_engine_multiselect.py
git commit -m "feat: update generate_persona_tags for multi-select arrays"
```

---

### Task 6: Full integration verification

**Files:**
- Modify: `tests/test_engine_multiselect.py`

- [ ] **Step 1: Write an integration test that exercises the full recommend flow**

Add to `tests/test_engine_multiselect.py`:

```python
def test_full_flow_multi_select():
    """Integration: full engine flow with multi-select QA."""
    engine = _make_engine(reg_year=2023, displacement=1998)

    qa = AnalysisQA(
        passenger_preference=["high_passenger_medical", "high_driver_disability"],
        vehicle_protection=["repair_perfectionist", "waive_subrogation"],
        liability_concern=["high_excess_liability", "high_property_damage"],
        service_needs=["roadside_assistance_100km", "legal_expense", "consolation_money"],
        budget_profile=["safety_first"],
    )
    engine.apply_questionnaire(qa)

    # Verify indices are within valid ranges
    from app.constants.insurance_rates import MAX_INDEX
    for k, v in engine.indices.items():
        if v > 0:
            assert 1 <= v <= MAX_INDEX[k], f"{k} index {v} out of range"

    # Verify items can be built
    items = engine.build_items()
    assert len(items) > 0

    # Verify premium calculation works
    premium = engine.calculate_premium()
    assert premium["voluntary"] > 0
    assert premium["compulsory"] > 0

    # Verify radar calculation works
    radar = engine.calculate_radar()
    for dim in ["passenger_preference", "vehicle_protection", "liability_concern",
                "service_needs", "budget_profile"]:
        assert 70 <= radar[dim] <= 95

    # Verify persona tags include multi-select tags
    tags = engine.generate_persona_tags(qa)
    assert "重視家人安全" in tags
    assert "家庭經濟支柱" in tags
    assert "愛車完美主義" in tags

    # Verify insurance code generation
    code = engine.generate_insurance_code()
    assert len(code) > 0
    assert code[0] == "A"  # A is always present
```

- [ ] **Step 2: Run all tests**

Run: `python -m pytest tests/test_engine_multiselect.py -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_engine_multiselect.py
git commit -m "test: add full integration test for multi-select flow"
```

---