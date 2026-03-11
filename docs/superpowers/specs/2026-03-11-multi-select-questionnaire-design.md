# Multi-Select Questionnaire Design

## Overview

Convert the insurance recommendation questionnaire from single-select to multi-select for all five categories. Selected options' effects stack additively, with absolute settings taking priority over relative shifts.

## Current State

- Five questionnaire categories, each single-select (`Optional[str]`)
- Each option applies a fixed effect: either a relative shift (+/-N) or an absolute assignment (=N) to insurance indices
- `finalize()` clamps indices to valid ranges: `< 0 → 0` (disabled), `== 0 → 0` (stays disabled), `> 0 → [1, MAX_INDEX]`

## Requirements

1. All five categories become multi-select (`Optional[List[str]]`)
2. **Categories are processed sequentially in order (1 → 2 → 3 → 4 → 5)**. Within each category, two-phase processing applies:
   - **Phase 1 (Relative shifts)**: Apply all +/- effects cumulatively
   - **Phase 2 (Absolute settings)**: Overwrite with absolute assignments
   - Budget_profile (category 5) sees the cumulative result of categories 1-4
3. If multiple absolute assignments target the same index within the same category's Phase 2, the last one in array order wins
4. "All enabled" means all indices with value > 0 **at the time that option is processed**
5. Existing `finalize()` clamp logic is reused unchanged
6. Old single-string format is no longer supported (frontend will send arrays)
7. Unknown option values within a category array are silently ignored (consistent with current behavior)

## Option Classification

### Category 1: passenger_preference (affects C, D)

| Option | Type | Effect |
|--------|------|--------|
| `high_passenger_medical` | Relative | C += 1 |
| `high_driver_disability` | Relative | D += 1 |
| `basic_passenger` | Relative | C -= 2 |
| `high_driver_medical` | Relative | D += 1 |

### Category 2: vehicle_protection (affects E, F, H)

| Option | Type | Effect |
|--------|------|--------|
| `repair_perfectionist` | Relative | E -= 1 (upgrade, E is reversed) |
| `waive_subrogation` | **Absolute** | F = 3 |
| `theft_protection` | **Absolute** | H = 1 |
| `basic_repair` | Relative | E += 2 (downgrade) |

### Category 3: liability_concern (affects A, B, K)

| Option | Type | Effect |
|--------|------|--------|
| `high_excess_liability` | Relative | B += 2 |
| `high_bodily_injury` | **Absolute** | K = 3 |
| `statutory_minimum` | Relative | A -= 1, B -= 1 |
| `high_property_damage` | Relative | A += 1 |

### Category 4: service_needs (affects G, I, J)

| Option | Type | Effect |
|--------|------|--------|
| `roadside_assistance_100km` | **Absolute** | G = 4 |
| `legal_expense` | **Absolute** | I = 3 |
| `consolation_money` | **Absolute** | J = 3 |
| `basic_roadside` | Relative | G -= 1 |

### Category 5: budget_profile (affects all enabled products)

| Option | Type | Effect |
|--------|------|--------|
| `safety_first` | Relative | All enabled +1 (E -1) |
| `best_value` | No-op | — |
| `budget_saver` | **Absolute** | All enabled = 1 (E = 4) |
| `ai_balanced` | No-op | — |

## Changes Required

### 1. `app/models/request.py` — AnalysisQA

Change all five fields from `Optional[str]` to `Optional[List[str]]`:

```python
from typing import Optional, List

class AnalysisQA(BaseModel):
    passenger_preference: Optional[List[str]] = None
    vehicle_protection: Optional[List[str]] = None
    liability_concern: Optional[List[str]] = None
    service_needs: Optional[List[str]] = None
    budget_profile: Optional[List[str]] = None
```

### 2. `app/services/insurance_engine.py` — apply_questionnaire()

Rewrite to two-phase processing, categories processed sequentially 1 → 5:

```
For category in [passenger_preference, vehicle_protection, liability_concern, service_needs, budget_profile]:
  selections = qa.<category> or []
  Phase 1: For each selection in selections, if it's a relative shift, apply it
  Phase 2: For each selection in selections, if it's an absolute assignment, apply it
finalize()
```

Key processing logic for budget_profile (global effects):
- `safety_first` (relative): iterate all indices with value > 0 at that moment, +1 each (E: -1)
- `budget_saver` (absolute): iterate all indices with value > 0 at that moment, set to 1 (E: set to 4)
- Absolute runs after relative, so budget_saver overrides safety_first

### 3. `app/services/insurance_engine.py` — generate_persona_tags()

Change from reading single string to iterating over arrays. Tags are collected in category order. Each selected option value is looked up in `PERSONA_TAG_MAP`; missing entries are silently skipped.

### 4. Backward Compatibility

- `null` or `[]` → skip (same as not answering)
- `["single_value"]` → equivalent to old single-select behavior
- Single string format no longer accepted (breaking change for API consumers)

## Example Scenarios

### Scenario 1: Opposing selections cancel out
```json
{
  "passenger_preference": ["high_passenger_medical", "basic_passenger"]
}
```
- Phase 1: C += 1, then C -= 2 → net C -= 1
- Phase 2: no absolutes
- Result: C index decreases by 1

### Scenario 2: Absolute overrides relative (different indices)
```json
{
  "vehicle_protection": ["repair_perfectionist", "waive_subrogation"]
}
```
- Phase 1: E -= 1 (relative)
- Phase 2: F = 3 (absolute, targets different index than E)
- Result: E upgraded by 1, F set to 3

### Scenario 3: Budget conflict
```json
{
  "budget_profile": ["safety_first", "budget_saver"]
}
```
- Phase 1: safety_first → all enabled +1 (E -1)
- Phase 2: budget_saver → all enabled set to 1, E set to 4 (overwrites phase 1)
- Result: all enabled indices set to lowest tier (budget_saver wins)

### Scenario 4: Cross-category interaction
```json
{
  "vehicle_protection": ["repair_perfectionist"],
  "budget_profile": ["budget_saver"]
}
```
Assuming base indices from car-age anchoring: E=2, A=3, B=3, C=3, D=3, F=3, G=3, etc.

1. Category 2 (vehicle_protection):
   - Phase 1: E -= 1 → E becomes 1 (upgraded)
   - Phase 2: no absolutes selected
2. Categories 3, 4: no selections, skip
3. Category 5 (budget_profile):
   - Phase 1: no relative options selected
   - Phase 2: budget_saver → all enabled indices set to 1, E set to 4
   - E was 1, now set to 4 (budget_saver overwrites the vehicle_protection upgrade)
   - A=1, B=1, C=1, D=1, F=1, G=1, etc.
4. `finalize()`: clamp all to valid ranges

Result: budget_saver dominates, vehicle_protection upgrade is overwritten.

## Files Affected

| File | Change |
|------|--------|
| `app/models/request.py` | AnalysisQA field types (`Optional[str]` → `Optional[List[str]]`), add `List` import |
| `app/services/insurance_engine.py` | `apply_questionnaire()`, `generate_persona_tags()` |

## Out of Scope

- Insurance company API integration (deferred, to be designed separately)
- Frontend UI changes (handled by frontend team)
- New question options (only changing selection mechanism)
