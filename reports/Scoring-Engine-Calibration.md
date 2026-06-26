# Scoring Engine Calibration Report

This report documents the scoring criteria weights, signal definitions, threshold justification, and calibration test cases for the deterministic `ScoringEngine` used in Heritage Sentinel AI.

---

## 1. Scoring Architecture Overview

The `ScoringEngine` (`backend/app/agents/scoring_engine.py`) is entirely separate from Gemini. It reads `data/scoring_criteria.json` (cached via `@lru_cache`) and scores the five evidence text fields extracted by `EvaluationAgent`.

**Principle**: Identical input text always produces identical scores. No model variance. No randomness.

---

## 2. Scoring Breakdown (Max 100 Points)

| Category | Max Points | Evidence Field Scored |
| :--- | :---: | :--- |
| Historic Features | **30** | `historic_features` |
| Cultural Significance | **25** | `cultural_significance` |
| Geographic Context | **15** | `geographic_context` |
| Documentation Quality | **15** | `documentation_quality` |
| Supporting Evidence | **15** | `supporting_evidence` + photo count bonus |
| **Total** | **100** | |

### Photo Bonus (Supporting Evidence)
A photo count bonus of `+2 per photo` is applied to the `supporting_evidence` score, capped at `+5` maximum. This ensures submissions with no photos are not penalised beyond their text evidence, while rewarding visual documentation.

---

## 3. Signal Tiers per Category

### Historic Features (Max: 30)

| Tier | Score Range | Example Signals |
| :--- | :---: | :--- |
| Outstanding | 25–30 | `century`, `AD`, `BC`, `BCE`, `dynasty`, `empire`, `excavation`, `archaeological`, `megalithic`, `prehistoric` |
| Significant | 15–24 | `historical`, `ancient`, `medieval`, `colonial`, `ruins`, `temple`, `monastery`, `fortress`, `palace` |
| Limited | 5–14 | `old`, `traditional`, `historic`, `past`, `former`, `original` |
| Insufficient | 0–4 | *(no signals)* |

### Cultural Significance (Max: 25)

| Tier | Score Range | Example Signals |
| :--- | :---: | :--- |
| Outstanding | 20–25 | `UNESCO`, `world heritage`, `universal value`, `pilgrimage`, `sacred`, `intangible`, `living tradition`, `masterpiece`, `exceptional` |
| Significant | 12–19 | `religious`, `spiritual`, `cultural`, `artistic`, `symbolic`, `festival`, `ceremony`, `community`, `indigenous`, `folk` |
| Limited | 4–11 | `local`, `regional`, `significance`, `important`, `valued`, `meaningful` |
| Insufficient | 0–3 | *(no signals)* |

### Geographic Context (Max: 15)

| Tier | Score Range | Example Signals |
| :--- | :---: | :--- |
| Outstanding | 12–15 | `landscape`, `ecosystem`, `biodiversity`, `geological`, `basin`, `volcanic`, `tectonic`, `endemic`, `watershed` |
| Notable | 7–11 | `located in`, `situated`, `region`, `province`, `coordinates`, `elevation`, `river`, `mountain`, `forest`, `island` |
| Generic | 2–6 | `area`, `zone`, `place`, `site`, `location`, `nearby`, `surrounding` |
| Insufficient | 0–1 | *(no signals)* |

### Documentation Quality (Max: 15)

| Tier | Score Range | Example Signals |
| :--- | :---: | :--- |
| Extensive | 12–15 | `published`, `academic`, `research`, `survey`, `ASI`, `UNESCO`, `ICOMOS`, `archive`, `peer-reviewed`, `carbon dating`, `scientific` |
| Partial | 7–11 | `documented`, `records`, `historical account`, `government`, `museum`, `inscription`, `manuscript`, `map` |
| Anecdotal | 2–6 | `mentioned`, `known`, `reportedly`, `oral`, `tradition`, `legend`, `local knowledge` |
| None | 0–1 | *(no signals)* |

### Supporting Evidence (Max: 15)

| Tier | Score Range | Example Signals |
| :--- | :---: | :--- |
| Strong | 12–15 | `high-quality`, `detailed`, `multiple photos`, `aerial`, `drone`, `professional`, `high resolution`, `360` |
| Adequate | 7–11 | `photos provided`, `photographs`, `images`, `photo`, `image`, `video` |
| Minimal | 2–6 | `one photo`, `single image`, `limited`, `low quality`, `blurry`, `distant` |
| Absent | 0–1 | *(no signals)* |

---

## 4. Threshold Justification

### Auto-Rejection Threshold: 60 / 100

Submissions scoring **< 60** are automatically rejected by `VerificationAgent` with status `rejected` and a note explaining the score. Submissions scoring **≥ 60** are routed to the human archaeologist review queue.

**Rationale**:
- Score < 60 implies the submission lacks credible evidence in at least 2–3 major categories.
- Score ≥ 60 (Medium Confidence) means there is enough signal for an expert to make an informed human decision.
- Score ≥ 80 (High Confidence) is treated as a strong candidate and labelled accordingly on the Confidence Card.

> ⚠️ **DEBT-06**: The threshold value `60` is hardcoded as `_AUTO_REJECT_THRESHOLD = 60` in `verification_agent.py`. It should be externalised to `scoring_criteria.json` or an environment variable to allow tuning without a code deploy.

---

## 5. Calibration Test Cases

The following representative test cases illustrate expected score ranges for various submission quality levels.

### Case 1: Strong Heritage Candidate (Expected Score: 75–90)
**Input signals present**: `14th century`, `dynasty`, `excavation`, `archaeological`, `pilgrimage`, `sacred`, `UNESCO`, `documented`, `ASI`, `river basin`, `multiple photos`
- Historic Features: ~27/30 (Outstanding tier, high signal density)
- Cultural Significance: ~22/25 (Outstanding tier, UNESCO/pilgrimage signals)
- Geographic Context: ~10/15 (Notable tier, river basin)
- Documentation: ~13/15 (Extensive tier, ASI/UNESCO/documented)
- Supporting Evidence: ~11/15 (Adequate tier + photo bonus)
- **Expected Total: ~83/100** — Routes to `verification` ✅

### Case 2: Moderate Candidate (Expected Score: 60–75)
**Input signals present**: `ancient`, `temple`, `religious`, `cultural`, `regional significance`, `government records`, `located in`, `photos provided`
- Historic Features: ~18/30 (Significant tier, moderate density)
- Cultural Significance: ~15/25 (Significant tier)
- Geographic Context: ~8/15 (Notable tier)
- Documentation: ~9/15 (Partial tier)
- Supporting Evidence: ~8/15 (Adequate tier + 1 photo)
- **Expected Total: ~58–68/100** — Borderline; may route to `verification` or be rejected

### Case 3: Weak Submission (Expected Score: 10–35)
**Input signals present**: `old building`, `local area`, `mentioned by elders`, `one photo`
- Historic Features: ~7/30 (Limited tier)
- Cultural Significance: ~6/25 (Limited tier)
- Geographic Context: ~3/15 (Generic tier)
- Documentation: ~3/15 (Anecdotal tier)
- Supporting Evidence: ~4/15 (Minimal tier + 1 photo)
- **Expected Total: ~23/100** — Auto-rejected ✅

### Case 4: Boundary Score (Score = 60, Expected: Routes to Verification)
- The `VerificationAgent` uses `< 60` for rejection, meaning a score of exactly **60** routes to `verification`.
- Test `test_verification_routes_boundary_score_60` in `tests/test_evaluation_agent.py` confirms this boundary is inclusive. ✅

### Case 5: Gemini Extraction Failure (Expected Score: ~0–5)
- When Gemini fails, all evidence fields are set to `"Extraction unavailable — evaluation service error."`
- The word `"unavailable"` causes `_score_field` to return `0` for all categories (explicit early return).
- Photo bonus may add up to +5.
- **Expected Total: 0–5/100** — Auto-rejected ✅
- Test `test_evaluation_agent_handles_gemini_failure` verifies `total < 10`. ✅

---

## 6. Known Gaps & Recommendations

| Gap | Impact | Recommendation |
| :--- | :--- | :--- |
| Signal matching is **substring-only** — no stemming or NLP | Signals like `"archaeological"` won't match `"archaeologically"` | Add simple stemming or lemmatisation to `_score_field` |
| No cross-category signal deduplication | Same word counted separately in multiple categories | Acceptable for MVP; revisit for v2 |
| Threshold `60` is hardcoded | Cannot adjust sensitivity without a code change | Move to `scoring_criteria.json` or env variable |
| No calibration against real UNESCO data | Scores not validated against known high-quality sites | Run calibration batch against all 41 seeded sites once dataset is expanded |
| `documentation` key mismatch | `criteria["documentation"]` vs field named `documentation_quality` in `ExtractedEvidence` | Verify key consistency between JSON and model — currently works but fragile |
