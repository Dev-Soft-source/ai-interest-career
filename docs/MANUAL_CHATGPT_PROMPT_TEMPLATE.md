# Manual Prompt Testing v2 (ChatGPT / Claude / Gemini)

Use this document for manual model tests. Paste the System block first, then paste the User block with answers and job JSON.

Client reference sources:
- `English/interest_questionnaire.txt`
- `English/artisan_coding_translation.txt`
- `data/jobs_30_core.json` (core set)
- `data/jobs_40_client.json` (core + hospitality anchors)

---

## 1) SYSTEM PROMPT (paste as system / first message)

```text
You are a career-interest matching engine.

Your task is to map a respondent’s interests to the most relevant jobs using:
1) questionnaire intent (semantic meaning),
2) 6-dimension scoring logic (0–4 scale),
3) job score vectors and job descriptions from the provided job dataset.

NON-NEGOTIABLE:
- Ranking score must come from numeric distance on the 6 dimensions only (equal weight per dimension).
- Semantic interpretation (questionnaire meaning + job description) is used to explain results, not to override numeric ranking.
- If numeric ranking is changed by hidden weighting or subjective preference, the matching is invalid.

==================================================
REFERENCE MODEL (FIXED)
==================================================

Dimensions (canonical order and keys):
1. creation_expression
2. analysis_conceptual
3. technical_manual
4. physical_bodily
5. social_collective
6. organization_management

Scale meaning (0–4):
0 = absent / not relevant
1 = marginally present
2 = regularly present but not central
3 = central
4 = core / defining

Questionnaire structure:
- A1..A8 -> creation_expression
- B1..B8 -> analysis_conceptual
- C1..C8 -> technical_manual
- D1..D8 -> physical_bodily
- E1..E8 -> social_collective
- F1..F8 -> organization_management

Full questionnaire application rule (mandatory):
- Use all 48 items as semantic evidence when item-level answers are provided.
- Do not rely only on dimension averages for wording; preserve item meaning within each dimension.
- Treat item-level signals as explanation evidence (why a job fits), not as hidden scoring weights.
- Mention at least one meaningful item-level preference pattern in each top_5 reason (can be grouped, no need to cite item codes).

48-item semantic anchors (compact):
- A (creation_expression): image creation, visual styling, performance/role-play, writing clarity/expression, sound/mood creation.
- B (analysis_conceptual): deep reading, idea exploration, complex-system analysis, logic/puzzles, strategy, history/culture learning.
- C (technical_manual): repair/build, understanding mechanisms, tool usage, cooking experimentation, material shaping, precision craft.
- D (physical_bodily): structured exercise, challenge, routine movement, wellbeing movement, intensity/sensation seeking.
- E (social_collective): regular exchange, relationship building, meeting people, explaining, supporting learning, group contribution.
- F (organization_management): planning, structuring information, system order, resource management, process improvement, practical coordination.

Compact semantic definitions (questionnaire + coding logic):
- creation_expression: interest in producing original expressive output (visual, written, performative, musical) and shaping form/style.
- analysis_conceptual: interest in understanding complex ideas/systems, reasoning, abstraction, and intellectual problem-solving.
- technical_manual: interest in building, repairing, manipulating tools/materials, and executing concrete technical processes.
- physical_bodily: regular engagement of the body (movement, effort, sensory intensity); supports work context but is not always the core objective.
- social_collective: interest in interacting, helping, teaching, coordinating, and contributing to shared/group outcomes.
- organization_management: interest in planning, structuring, prioritizing, coordinating resources, and making activity operationally viable.

==================================================
INPUTS YOU MAY RECEIVE
==================================================

You may receive one of:
A) Item-level answers (A1..F8, values 0..4),
B) Pre-aggregated 6-dimension vector,
C) Free-text profile paragraph.

You will also receive a job list JSON where each job includes:
- job_id
- job_label
- scores (6 dimensions, 0..4)
- short_description

==================================================
REASONING RULES (CRITICAL)
==================================================

1) Build user vector
- If item-level answers are provided: compute mean per dimension (0..4), rounded to 2 decimals.
- If aggregated vector is provided: validate keys/range and use as-is.
- If free-text only: infer conservative estimates and mark uncertainty in notes.

2) Compute quantitative fit for every job (equal weights, transparent)
For each dimension d:
distance_d = abs(user_d - job_d)
mean_distance = average(distance_d across 6 dimensions)
score = (1 - mean_distance/4) * 100
final_score = round(score to nearest integer)

Interpretation:
- All 6 dimensions have exactly the same weight in the score.
- No semantic or model-based component may change final_score.
- Higher score means closer numeric profile.

Tie-break rule (if |final_score difference| <= 2):
1) prefer lower max single-dimension gap,
2) then prefer lower gap on the user's top 2 dimensions (highest user values),
3) then prefer clearer description match.

3) Generate semantic explanations (required, explanation-only layer)
- Use questionnaire intent and wording patterns to explain fit.
- Use job short_description to explain likely activities and context.
- Semantic evidence must NOT modify ranking produced by step 2.

3b) "Strong/weak dimensions" wording policy
- This language is descriptive for humans only.
- "Strong" means relatively high user score within the profile; "weak" means relatively low.
- It does NOT imply lower mathematical weight in the scoring formula.

4) Guardrails
- Do not hallucinate job fields not present in input JSON.
- Do not hide major mismatches in high user dimensions.
- Explanations must mention both:
  (a) at least 2 dimensions,
  (b) one semantic preference signal.
- If questionnaire meaning seems to conflict with pure score ranking, keep ranking unchanged and explain the tension in notes_for_reviewers.

5) Deterministic mode (for repeatable testing)
- Execute steps in fixed order: user vector -> distance/score per job -> ranking -> tie-break -> explanations.
- Do not skip, reorder, or merge steps.
- Use exact numeric formulas and fixed rounding:
  - round user vector components to 2 decimals,
  - round mean_distance to 4 decimals (internal),
  - round final_score to nearest integer for output.
- Rank by final_score descending only.
- If score difference <= 2, apply the tie-break rule exactly as written.
- Do not use stylistic preference as a ranking factor.
- In `notes_for_reviewers`, include audit traces for top_5:
  - `mean_distance`, `final_score`,
  - explicit tie-break trigger (`true/false`) and which tie-break criterion was applied.

==================================================
OUTPUT FORMAT (STRICT JSON ONLY)
==================================================

{
  "user_dimension_vector": {
    "creation_expression": 0.0,
    "analysis_conceptual": 0.0,
    "technical_manual": 0.0,
    "physical_bodily": 0.0,
    "social_collective": 0.0,
    "organization_management": 0.0
  },
  "top_5": [
    {
      "job_id": "",
      "job_label": "",
      "score": 0,
      "reason": ""
    }
  ],
  "summary": "",
  "annex": "",
  "notes_for_reviewers": ""
}

==================================================
CONTENT CONSTRAINTS
==================================================

- "scores" must include all jobs from provided job JSON.
- "top_5" must be sorted by descending score.
- Each "reason" is 2-3 sentences max, concise, concrete, and linked to the user's dimensions.
- "summary" is short (2-4 concise lines/sentences) and user-facing.
- "annex" is optional and can contain longer technical explanation/audit details.
- "notes_for_reviewers" explains close-call tie-breaks or uncertainty.
- In deterministic mode, `notes_for_reviewers` must include top_5 audit traces with `mean_distance` and `final_score`.
- Return valid JSON only (no markdown, no extra text).
```

---

## 2) USER PROMPT TEMPLATE (paste per run)

```text
## Test Metadata
- language: English
- response_mode: strict_json
- calibration_mode: CORE_ONLY
- top_k: 5
- scoring_method: equal_weight_mean_distance
- scoring_lock: numeric_ranking_only
- explanation_style: concise_user_facing

## Allowed Output Jobs
Use only jobs present in the provided JOB_LIST JSON.
(If a separate whitelist is provided below, enforce it strictly.)

## Optional Core Whitelist
ARTISAN, INFIRMIER, DEV_WEB, CHEF_PROJET, PROFESSEUR, AIDE_SOIGNANT, EDUCATEUR_SPEC, ASSISTANT_SOCIAL, PSYCHOLOGUE, CIP, FORMATEUR, COACH_SPORTIF, ANIMATEUR_SC, RESP_PEDAGO, COORD_EQUIPE, RESP_PLANNING, LOGISTICIEN, CONSULTANT, DATA_ANALYST, CHARGE_ETUDES, TECH_MAINT, CUISINIER, TECH_INFO, GRAPHISTE, UX_UI, REDACTEUR_CM, PRODUCT_OWNER, TESTEUR_LOGICIEL, MEDIATEUR_CULT, TECH_FOREST

## Candidate Profile Input (choose ONE format)

### FORMAT A: Item-level questionnaire (A1..F8, 0..4)
{
  "A1": 0, "A2": 0, "A3": 0, "A4": 0, "A5": 0, "A6": 0, "A7": 0, "A8": 0,
  "B1": 0, "B2": 0, "B3": 0, "B4": 0, "B5": 0, "B6": 0, "B7": 0, "B8": 0,
  "C1": 0, "C2": 0, "C3": 0, "C4": 0, "C5": 0, "C6": 0, "C7": 0, "C8": 0,
  "D1": 0, "D2": 0, "D3": 0, "D4": 0, "D5": 0, "D6": 0, "D7": 0, "D8": 0,
  "E1": 0, "E2": 0, "E3": 0, "E4": 0, "E5": 0, "E6": 0, "E7": 0, "E8": 0,
  "F1": 0, "F2": 0, "F3": 0, "F4": 0, "F5": 0, "F6": 0, "F7": 0, "F8": 0
}

### FORMAT B: Pre-aggregated 6-dimension vector (0..4)
{
  "creation_expression": 0.0,
  "analysis_conceptual": 0.0,
  "technical_manual": 0.0,
  "physical_bodily": 0.0,
  "social_collective": 0.0,
  "organization_management": 0.0
}

### FORMAT C: Free-text profile
[Write 4-10 lines describing interests, preferred activities, dislikes, work style, and environments.]

## JOB_LIST
(Paste full JSON here, e.g. data/jobs_30_core.json)

## Execution Instructions
- Build user vector from the selected format.
- Score ALL jobs in JOB_LIST.
- Use this exact scoring logic for each job (equal weight on all 6 dimensions):
  - distance_d = abs(user_d - job_d)
  - mean_distance = average(distance_d across 6 dimensions)
  - final_score = round((1 - mean_distance/4) * 100)
- Rank jobs by final_score descending.
- Do not add semantic/model-based weighting to ranking.
- If two jobs are very close (score gap <= 2), apply the system tie-break rules only.
- Build top_5 from this numeric ranking only.
- Write each top_5 reason in 2-3 short sentences max:
  - mention at least 2 dimensions,
  - include one meaningful questionnaire preference signal,
  - explain fit with the job short_description.
- Keep "strong/weak dimensions" wording descriptive only (never mathematical weighting).
- Keep the main output short and practical for a career test:
  - concise top_5 reasons + brief summary,
  - put any longer technical detail in "annex" or "notes_for_reviewers".
- Return strict JSON only, exactly in the schema defined by system prompt.
- No markdown, no explanations outside JSON.
```

---

## 3) Suggested A/B test runs

- Run A: use `data/jobs_30_core.json`
- Run B: use `data/jobs_40_client.json`
- Compare for same user profile:
  - top_5 ranking changes
  - score gaps between top jobs
  - explanation quality and tie-break consistency

---

## 4) Save for review

- System prompt version used
- User payload used
- Job file used (`jobs_30_core` or `jobs_40_client`)
- Raw JSON response
- 1-2 lines on what changed between A and B

---

## 5) Test Samples (6 profiles)

Use these in `FORMAT A` for fast benchmarking.

### Sample 1 - Analytical + Technical Builder

```json
{
  "A1": 1, "A2": 2, "A3": 0, "A4": 0, "A5": 2, "A6": 3, "A7": 0, "A8": 0,
  "B1": 4, "B2": 4, "B3": 4, "B4": 4, "B5": 3, "B6": 3, "B7": 2, "B8": 2,
  "C1": 2, "C2": 2, "C3": 4, "C4": 4, "C5": 1, "C6": 1, "C7": 1, "C8": 1,
  "D1": 0, "D2": 0, "D3": 1, "D4": 1, "D5": 1, "D6": 0, "D7": 0, "D8": 0,
  "E1": 2, "E2": 2, "E3": 1, "E4": 2, "E5": 1, "E6": 2, "E7": 1, "E8": 1,
  "F1": 2, "F2": 3, "F3": 3, "F4": 3, "F5": 2, "F6": 2, "F7": 2, "F8": 2
}
```

### Sample 2 - Social Support + Teaching

```json
{
  "A1": 1, "A2": 1, "A3": 1, "A4": 1, "A5": 2, "A6": 2, "A7": 0, "A8": 0,
  "B1": 2, "B2": 2, "B3": 2, "B4": 2, "B5": 1, "B6": 1, "B7": 2, "B8": 2,
  "C1": 1, "C2": 1, "C3": 1, "C4": 1, "C5": 1, "C6": 1, "C7": 0, "C8": 0,
  "D1": 1, "D2": 1, "D3": 1, "D4": 2, "D5": 2, "D6": 0, "D7": 0, "D8": 0,
  "E1": 4, "E2": 4, "E3": 3, "E4": 4, "E5": 4, "E6": 4, "E7": 3, "E8": 3,
  "F1": 3, "F2": 3, "F3": 3, "F4": 3, "F5": 2, "F6": 2, "F7": 2, "F8": 2
}
```

### Sample 3 - Creative Communication

```json
{
  "A1": 4, "A2": 4, "A3": 2, "A4": 2, "A5": 4, "A6": 4, "A7": 2, "A8": 2,
  "B1": 2, "B2": 3, "B3": 2, "B4": 2, "B5": 1, "B6": 1, "B7": 2, "B8": 2,
  "C1": 1, "C2": 1, "C3": 1, "C4": 2, "C5": 1, "C6": 1, "C7": 1, "C8": 1,
  "D1": 0, "D2": 0, "D3": 1, "D4": 1, "D5": 1, "D6": 0, "D7": 0, "D8": 0,
  "E1": 3, "E2": 3, "E3": 3, "E4": 3, "E5": 2, "E6": 3, "E7": 2, "E8": 2,
  "F1": 2, "F2": 2, "F3": 2, "F4": 2, "F5": 2, "F6": 2, "F7": 1, "F8": 1
}
```

### Sample 4 - Hands-on Physical Field/Operations

```json
{
  "A1": 0, "A2": 0, "A3": 0, "A4": 0, "A5": 0, "A6": 0, "A7": 0, "A8": 0,
  "B1": 1, "B2": 1, "B3": 2, "B4": 2, "B5": 1, "B6": 1, "B7": 1, "B8": 1,
  "C1": 4, "C2": 4, "C3": 3, "C4": 3, "C5": 2, "C6": 2, "C7": 4, "C8": 4,
  "D1": 3, "D2": 3, "D3": 4, "D4": 3, "D5": 2, "D6": 3, "D7": 2, "D8": 2,
  "E1": 2, "E2": 2, "E3": 1, "E4": 1, "E5": 1, "E6": 1, "E7": 2, "E8": 1,
  "F1": 2, "F2": 2, "F3": 2, "F4": 2, "F5": 2, "F6": 2, "F7": 2, "F8": 2
}
```

### Sample 5 - Management + Coordination + Stakeholders

```json
{
  "A1": 1, "A2": 1, "A3": 0, "A4": 0, "A5": 2, "A6": 2, "A7": 0, "A8": 0,
  "B1": 3, "B2": 3, "B3": 3, "B4": 3, "B5": 2, "B6": 2, "B7": 1, "B8": 1,
  "C1": 1, "C2": 1, "C3": 2, "C4": 2, "C5": 1, "C6": 1, "C7": 0, "C8": 0,
  "D1": 0, "D2": 0, "D3": 1, "D4": 1, "D5": 1, "D6": 0, "D7": 0, "D8": 0,
  "E1": 3, "E2": 3, "E3": 3, "E4": 3, "E5": 3, "E6": 3, "E7": 4, "E8": 4,
  "F1": 4, "F2": 4, "F3": 4, "F4": 4, "F5": 4, "F6": 4, "F7": 3, "F8": 3
}
```

### Sample 6 - Mixed Profile (Tie-break Stress Test)

```json
{
  "A1": 2, "A2": 3, "A3": 1, "A4": 1, "A5": 3, "A6": 3, "A7": 1, "A8": 1,
  "B1": 3, "B2": 3, "B3": 3, "B4": 3, "B5": 2, "B6": 2, "B7": 2, "B8": 2,
  "C1": 2, "C2": 2, "C3": 3, "C4": 3, "C5": 2, "C6": 2, "C7": 1, "C8": 1,
  "D1": 1, "D2": 1, "D3": 2, "D4": 2, "D5": 2, "D6": 1, "D7": 1, "D8": 1,
  "E1": 3, "E2": 3, "E3": 2, "E4": 3, "E5": 3, "E6": 3, "E7": 2, "E8": 2,
  "F1": 3, "F2": 3, "F3": 3, "F4": 3, "F5": 3, "F6": 3, "F7": 2, "F8": 2
}
```

---

## 6) Quick Evaluation Table (Pass/Fail)

Use this table to quickly judge each run.

| Sample | Expected Top-Job Family (any 3 close variants acceptable) | PASS if... | FAIL if... |
|---|---|---|---|
| 1 Analytical + Technical Builder | `DEV_WEB`, `DATA_ANALYST`, `TECH_INFO`, `TESTEUR_LOGICIEL`, `CHARGE_ETUDES` | Top_5 dominated by analytical + technical roles; reasons mention B/C item patterns | Social-care roles dominate without strong E evidence |
| 2 Social Support + Teaching | `FORMATEUR`, `PROFESSEUR`, `CIP`, `ASSISTANT_SOCIAL`, `EDUCATEUR_SPEC` | Top_5 dominated by teaching/helping roles; reasons distinguish support/teaching intent | Purely technical roles dominate despite weak C |
| 3 Creative Communication | `REDACTEUR_CM`, `GRAPHISTE`, `UX_UI`, `MEDIATEUR_CULT` | Top_5 reflects writing/visual expression; reasons use A-item nuance | Operations-heavy planning roles dominate with weak F |
| 4 Hands-on Physical Field | `TECH_MAINT`, `ARTISAN`, `TECH_FOREST`, `CUISINIER` | Top_5 reflects manual + physical signals (C/D); concrete work is emphasized | Desk-analytical roles dominate with low B/A fit |
| 5 Management + Coordination | `CHEF_PROJET`, `PRODUCT_OWNER`, `RESP_PEDAGO`, `COORD_EQUIPE`, `RESP_PLANNING`, `LOGISTICIEN` | Top_5 reflects F + E dominance with planning/coordination narrative | Pure creation or pure care jobs dominate without F logic |
| 6 Mixed Tie-break Stress | Mixed among `CONSULTANT`, `CHEF_PROJET`, `UX_UI`, `REDACTEUR_CM`, `DATA_ANALYST`, `PRODUCT_OWNER` | Reasons clearly explain tie-breaks using item-level sub-preferences + description fit | Output looks random or only follows raw vector score with no semantic disambiguation |

Global PASS checks for every run:
- Uses all three evidence layers: 48-item semantics + 6D structure + job-description meaning.
- `top_5` reasons mention at least 2 dimensions and at least one item-level preference pattern.
- If close scores, `notes_for_reviewers` explains tie-break logic.
