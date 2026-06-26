# Scoring Engine Calibration Report

This report documents the scoring criteria weights, signal definitions, threshold justification, and calibration test cases for the deterministic `ScoringEngine` used in Heritage Sentinel AI.

---

## 1. Scoring Architecture Overview

The `ScoringEngine` (`backend/app/agents/scoring_engine.py`) is entirely separate from Gemini. It reads `data/scoring_criteria.json` (cached via `@lru_cache`) and scores the five evidence text fields extracted by `EvaluationAgent`.

**Principle**: Identical input text always produces identical scores. No model variance. No randomness.

---

## 2. Scoring Breakdown (Max 100 Points for Core Pillars + 15 Supporting Evidence)

The scoring engine evaluates submissions across **8 dimensions** covering the three pillars of UNESCO evaluation (Outstanding Universal Value, Integrity/Authenticity, and Management/Protection):

| Category | Max Points | Evidence Field Scored | UNESCO Pillar / OUV Criteria |
| :--- | :---: | :--- | :--- |
| Historic Features | **25** | `historic_features` | OUV Criteria i, iii, iv |
| Cultural Significance | **20** | `cultural_significance` | OUV Criteria ii, v, vi |
| Integrity | **15** | `integrity` | Wholeness & intactness (All properties) |
| Authenticity | **15** | `authenticity` | Truthfulness & credibility (Cultural properties) |
| Geographic Context | **10** | `geographic_context` | OUV Criteria vii, viii, ix, x (Natural values) |
| Documentation Quality | **10** | `documentation_quality` | Nomination quality & academic basis |
| Management & Protection | **5** | `management_protection` | Legal protection & management plan |
| Supporting Evidence | **15** | `supporting_evidence` + photo bonus | Visual documentation quality |
| **Total Core Pillars** | **100** | *(Sum of first 7 categories)* | *(Capped at 100 max via Pydantic model validator)* |

### Photo Bonus (Supporting Evidence)
A photo count bonus of `+2 per photo` is applied to the `supporting_evidence` score, capped at `+5` maximum. The overall `supporting_evidence` score is capped at `15` maximum.

---

## 3. Signal Tiers per Category

### Historic Features (Max: 25)

| Tier | Score Range | Example Signals |
| :--- | :---: | :--- |
| Outstanding | 20–25 | `century`, `AD`, `BC`, `BCE`, `CE`, `dynasty`, `empire`, `civilisation`, `civilization`, `excavation`, `archaeological`, `dated to`, `masterpiece`, `creative genius` |
| Significant | 12–19 | `historical`, `ancient`, `medieval`, `colonial`, `ruins`, `remnants`, `heritage`, `era`, `period`, `age`, `fortress`, `palace`, `temple`, `monastery`, `citadel` |
| Limited | 4–11 | `old`, `traditional`, `historic`, `past`, `former`, `original`, `built`, `constructed`, `structure`, `building` |
| Insufficient | 0–3 | *(no signals)* |

### Cultural Significance (Max: 20)

| Tier | Score Range | Example Signals |
| :--- | :---: | :--- |
| Outstanding | 16–20 | `UNESCO`, `world heritage`, `universal value`, `pilgrimage`, `sacred`, `ritual`, `intangible`, `living tradition`, `cultural exchange`, `masterpiece`, `exceptional` |
| Significant | 9–15 | `religious`, `spiritual`, `cultural`, `artistic`, `symbolic`, `festival`, `ceremony`, `community`, `identity`, `ethnic`, `indigenous`, `folk`, `craft`, `music` |
| Limited | 3–8 | `local`, `regional`, `significance`, `important`, `valued`, `meaningful`, `celebrated`, `commemorated` |
| Insufficient | 0–2 | *(no signals)* |

### Integrity (Max: 15)

| Tier | Score Range | Example Signals |
| :--- | :---: | :--- |
| High Integrity | 12–15 | `intact`, `well-preserved`, `conservation`, `protected area`, `buffer zone`, `undisturbed`, `original condition`, `no encroachment`, `boundary protection`, `integrity` |
| Partial Integrity | 7–11 | `partially preserved`, `some damage`, `restored`, `restoration`, `maintained`, `maintenance`, `ongoing conservation`, `preservation`, `stabilised`, `repair` |
| Threatened | 2–6 | `threatened`, `at risk`, `deteriorating`, `vulnerable`, `encroachment`, `urban pressure`, `tourism pressure`, `climate risk`, `neglected`, `degraded`, `partial loss` |
| Unknown | 0–1 | *(no signals)* |

### Authenticity (Max: 15)

| Tier | Score Range | Example Signals |
| :--- | :---: | :--- |
| High Authenticity | 12–15 | `original materials`, `original form`, `original design`, `authentic`, `authenticity`, `traditional techniques`, `traditional craftsmanship`, `original fabric`, `unchanged` |
| Moderate Authenticity | 7–11 | `partly original`, `traditional style`, `reconstructed using`, `faithful reconstruction`, `historically accurate`, `traditional methods`, `local materials` |
| Low Authenticity | 2–6 | `reconstructed`, `rebuilt`, `replica`, `reproduction`, `modern reconstruction`, `partially reconstructed`, `restoration work`, `renovated`, `refurbished` |
| Unknown | 0–1 | *(no signals)* |

### Geographic Context (Max: 10)

| Tier | Score Range | Example Signals |
| :--- | :---: | :--- |
| Outstanding | 8–10 | `landscape`, `ecosystem`, `biodiversity`, `geological`, `topography`, `basin`, `plateau`, `valley`, `coast`, `estuary`, `volcanic`, `tectonic`, `endemic`, `habitat` |
| Notable | 5–7 | `located in`, `situated`, `region`, `province`, `district`, `coordinates`, `elevation`, `climate`, `terrain`, `geography`, `river`, `mountain`, `forest`, `desert` |
| Generic | 1–4 | `area`, `zone`, `place`, `site`, `location`, `nearby`, `surrounding`, `countryside` |
| Insufficient | 0 | *(no signals)* |

### Documentation Quality (Max: 10)

| Tier | Score Range | Example Signals |
| :--- | :---: | :--- |
| Extensive | 8–10 | `published`, `academic`, `research`, `study`, `survey`, `excavation report`, `archaeological survey`, `ASI`, `UNESCO`, `ICOMOS`, `IUCN`, `documented`, `archive` |
| Partial | 5–7 | `documented`, `historical account`, `colonial record`, `government`, `museum`, `inscription`, `text`, `manuscript`, `map`, `photograph`, `official record` |
| Anecdotal | 1–4 | `mentioned`, `known`, `reportedly`, `said to`, `believed`, `oral`, `tradition`, `legend`, `local knowledge`, `community account` |
| None | 0 | *(no signals)* |

### Management & Protection (Max: 5)

| Tier | Score Range | Example Signals |
| :--- | :---: | :--- |
| Strong | 4–5 | `management plan`, `protected by law`, `national legislation`, `conservation authority`, `heritage authority`, `national park`, `protected zone`, `legal protection` |
| Partial | 2–3 | `under government`, `government oversight`, `officially recognised`, `nationally recognised`, `state-owned`, `public ownership`, `heritage listing` |
| Unclear | 0–1 | *(no signals)* |

### Supporting Evidence (Max: 15)

| Tier | Score Range | Example Signals |
| :--- | :---: | :--- |
| Strong | 12–15 | `high-quality`, `detailed`, `multiple photos`, `interior`, `exterior`, `facade`, `sculpture`, `inscription visible`, `aerial`, `drone`, `professional` |
| Adequate | 7–11 | `photos provided`, `photographs`, `images`, `pictures`, `photo`, `image`, `snapshot`, `video`, `documentation provided` |
| Minimal | 2–6 | `one photo`, `single image`, `limited`, `low quality`, `blurry`, `distant`, `partial view` |
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

The following representative test cases illustrate expected score ranges for various submission quality levels, fully aligned with the unit test cases in `tests/test_evaluation_agent.py`.

### Case 1: Strong Heritage Candidate (Expected Score: 93/100)
**Input signals present**: `14th century`, `dynasty`, `excavation`, `archaeological`, `pilgrimage`, `sacred`, `UNESCO`, `original materials`, `intact`, `conservation`, `management plan`, `high-quality`
- Historic Features: ~22/25 (Outstanding tier, high signal density)
- Cultural Significance: ~18/20 (Outstanding tier, sacred/UNESCO/pilgrimage signals)
- Integrity: ~12/15 (High Integrity tier, intact/conservation signals)
- Authenticity: ~12/15 (High Authenticity tier, original materials)
- Geographic Context: ~8/10 (Outstanding tier, basin/landscape signals)
- Documentation Quality: ~8/10 (Extensive tier, ASI/UNESCO/documented signals)
- Management & Protection: ~3/5 (Partial tier)
- Supporting Evidence: ~10/15 (Adequate tier + photo bonus)
- **Expected Total: 93/100** — Routes to `verification` (High Confidence) ✅
- *Verified by*: `test_verification_routes_high_score_to_review` in `tests/test_evaluation_agent.py`

### Case 2: Borderline / Moderate Candidate (Expected Score: 60/100)
**Input signals present**: `ancient`, `temple`, `religious`, `cultural`, `partially preserved`, `traditional style`, `located in`, `documented`
- Historic Features: ~18/25 (Significant tier)
- Cultural Significance: ~14/20 (Significant tier)
- Integrity: ~8/15 (Partial Integrity tier)
- Authenticity: ~8/15 (Moderate Authenticity tier)
- Geographic Context: ~5/10 (Notable tier)
- Documentation Quality: ~5/10 (Partial tier)
- Management & Protection: ~2/5 (Partial tier)
- Supporting Evidence: ~0/15 (Absent)
- **Expected Total: 60/100** — Routes to `verification` (Medium Confidence) ✅
- *Verified by*: `test_verification_routes_boundary_score_60` in `tests/test_evaluation_agent.py`

### Case 3: Just Below Boundary (Expected Score: 59/100)
- Minor reduction in authenticity or integrity signals compared to Case 2 (e.g. Authenticity = 7/15 instead of 8/15).
- **Expected Total: 59/100** — Auto-rejected ✅
- *Verified by*: `test_verification_auto_rejects_score_59` in `tests/test_evaluation_agent.py`

### Case 4: Weak Submission (Expected Score: 19/100)
**Input signals present**: `old building`, `local area`, `mentioned by elders`, `one photo`, `some damage`, `reconstructed`
- Historic Features: ~5/25 (Limited tier)
- Cultural Significance: ~4/20 (Limited tier)
- Integrity: ~2/15 (Threatened tier)
- Authenticity: ~2/15 (Low Authenticity tier)
- Geographic Context: ~2/10 (Generic tier)
- Documentation Quality: ~2/10 (Anecdotal tier)
- Management & Protection: ~0/5 (Unclear tier)
- Supporting Evidence: ~2/15 (Minimal tier)
- **Expected Total: 19/100** — Auto-rejected ✅
- *Verified by*: `test_verification_auto_rejects_low_score` in `tests/test_evaluation_agent.py`

### Case 5: Gemini Extraction Failure (Expected Score: < 10)
- When Gemini fails, all evidence fields are set to `"Extraction unavailable — evaluation service error."`
- The word `"unavailable"` causes `_score_field` to return `0` for all categories (explicit early return).
- Photo bonus may add up to +5.
- **Expected Total: 0–5/100** — Auto-rejected ✅
- *Verified by*: `test_evaluation_agent_handles_gemini_failure` in `tests/test_evaluation_agent.py`

---

## 6. Known Gaps & Recommendations

| Gap | Impact | Recommendation |
| :--- | :--- | :--- |
| Signal matching is **substring-only** — no stemming or NLP | Signals like `"archaeological"` won't match `"archaeologically"` | Add simple stemming or lemmatisation to `_score_field` |
| No cross-category signal deduplication | Same word counted separately in multiple categories | Acceptable for MVP; revisit for v2 |
| Threshold `60` is hardcoded | Cannot adjust sensitivity without a code change | Move to `scoring_criteria.json` or env variable |
| No calibration against real UNESCO data | Scores not validated against known high-quality sites | Run calibration batch against all 41 seeded sites once dataset is expanded |
| `documentation` key mismatch | `criteria["documentation"]` vs field named `documentation_quality` in `ExtractedEvidence` | Verify key consistency between JSON and model — currently works but fragile |
