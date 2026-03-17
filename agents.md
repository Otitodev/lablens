# agents.md — LabLens MCP

> Medical Laboratory Intelligence MCP Server  
> Hackathon: Agents Assemble — The Healthcare AI Endgame (Devpost)  
> Platform: Prompt Opinion Marketplace  
> Protocol: Path A — MCP Server  
> Author: Otito | otito.site

---

## Overview

LabLens MCP is a FastAPI-based Model Context Protocol server that exposes four specialized medical laboratory AI tools. It is designed to be discovered and invoked from the Prompt Opinion platform, enabling clinicians and AI agents to reason over synthetic patient lab data using Claude as the underlying reasoning engine.

All data processed by this server is strictly synthetic and de-identified. No real Protected Health Information (PHI) is used at any layer.

---

## Agent card

The agent card is served at `/.well-known/agent.json` and follows the A2A/MCP discovery standard.

```json
{
  "name": "LabLens MCP",
  "description": "Medical laboratory intelligence server. Interprets lab panels, flags critical values, generates clinical summaries, and suggests differential diagnoses from abnormal result patterns.",
  "version": "1.0.0",
  "protocol": "mcp",
  "transport": ["http", "sse"],
  "author": "Otito",
  "contact": "otito.site",
  "data_policy": "synthetic_only",
  "phi": false,
  "tools": [
    "interpret_lab_panel",
    "flag_critical_values",
    "generate_clinical_summary",
    "suggest_differentials"
  ]
}
```

---

## Tools

### 1. `interpret_lab_panel`

Interprets a structured lab panel using Claude AI reasoning. Returns per-analyte commentary with clinical context, trend flags, and a brief overall assessment. Goes beyond reference-range flagging to surface clinical meaning.

**Endpoint:** `POST /tools/interpret_lab_panel`

**Input schema:**
```json
{
  "patient_id": "string (synthetic ID only)",
  "panel": "CBC | LFT | RENAL | COAG | THYROID | MIXED",
  "values": {
    "<analyte_name>": "<numeric_value>"
  },
  "units": "SI | conventional",
  "reference_ranges": {
    "<analyte_name>": { "low": 0.0, "high": 0.0 }
  }
}
```

**Output schema:**
```json
{
  "patient_id": "string",
  "panel": "string",
  "interpretations": [
    {
      "analyte": "string",
      "value": "number",
      "status": "normal | low | high | critical_low | critical_high",
      "commentary": "string",
      "clinical_significance": "string"
    }
  ],
  "overall_assessment": "string",
  "recommended_actions": ["string"]
}
```

**System prompt:**
```
You are a senior Medical Laboratory Scientist with 10 years of clinical experience.
You are interpreting laboratory results for a healthcare AI platform.
All patient data is synthetic and de-identified.

Your task is to:
1. Interpret each analyte value in clinical context, not just against reference ranges.
2. Identify patterns across analytes that suggest a clinical picture.
3. Flag values that require immediate clinical attention.
4. Provide your overall assessment in 2-3 sentences.
5. Suggest actionable next steps where appropriate.

Be precise. Use clinical terminology correctly. Do not give treatment advice — interpret findings only.
Respond in valid JSON matching the output schema provided.
```

---

### 2. `flag_critical_values`

Scans a result set for out-of-range values and returns a prioritized alert list. Critical values are those requiring immediate clinical notification. Designed for triage workflows where fast prioritization matters.

**Endpoint:** `POST /tools/flag_critical_values`

**Input schema:**
```json
{
  "patient_id": "string",
  "results": {
    "<analyte_name>": {
      "value": "number",
      "unit": "string",
      "reference_low": "number",
      "reference_high": "number",
      "critical_low": "number | null",
      "critical_high": "number | null"
    }
  }
}
```

**Output schema:**
```json
{
  "patient_id": "string",
  "alert_count": "number",
  "alerts": [
    {
      "analyte": "string",
      "value": "number",
      "severity": "critical | abnormal | borderline",
      "direction": "low | high",
      "message": "string",
      "notify_immediately": "boolean"
    }
  ],
  "summary": "string"
}
```

**System prompt:**
```
You are a clinical alert system for a medical laboratory.
All patient data is synthetic and de-identified.

Given a set of lab results, you must:
1. Identify critical values — those outside critical alert thresholds, requiring immediate clinician notification.
2. Identify abnormal values — those outside reference ranges but not critical.
3. Identify borderline values — those approaching the edges of reference ranges.
4. Sort alerts from most to least urgent.
5. For each alert, provide a brief, clinical message a nurse could act on.

Use the provided critical thresholds if given. If not provided, use standard clinical laboratory critical value thresholds.
Respond in valid JSON matching the output schema provided.
```

---

### 3. `generate_clinical_summary`

Generates a plain-English clinical narrative from a full lab report. Output is suitable for a patient chart note, a referral letter, or a handoff document. Designed to reduce documentation burden on clinicians.

**Endpoint:** `POST /tools/generate_clinical_summary`

**Input schema:**
```json
{
  "patient_id": "string",
  "patient_context": {
    "age_range": "string (e.g. 40s)",
    "sex": "male | female | unspecified",
    "clinical_indication": "string"
  },
  "results": {
    "<analyte_name>": {
      "value": "number",
      "unit": "string",
      "status": "normal | low | high | critical_low | critical_high"
    }
  },
  "summary_type": "chart_note | referral | patient_facing"
}
```

**Output schema:**
```json
{
  "patient_id": "string",
  "summary_type": "string",
  "summary": "string",
  "key_findings": ["string"],
  "word_count": "number"
}
```

**System prompt:**
```
You are a clinical documentation assistant for a medical laboratory AI platform.
All patient data is synthetic and de-identified.

Given a set of lab results and patient context, write a professional clinical summary.

Rules:
- chart_note: concise, clinical language, suitable for an EMR progress note. 150-250 words.
- referral: structured summary for a specialist. Include key findings, trend interpretation, and suggested workup. 200-300 words.
- patient_facing: plain language a non-clinician can understand. Avoid jargon. 100-200 words.

Always lead with the most clinically significant findings.
Do not give treatment recommendations.
Clearly state that results are from synthetic data if patient_facing.
Respond in valid JSON matching the output schema provided.
```

---

### 4. `suggest_differentials`

Takes a pattern of abnormal results and returns ranked differential diagnoses with brief reasoning per item. This is the primary AI Factor tool — it uses Claude's reasoning to surface clinically plausible diagnoses that no rule-based system can produce.

**Endpoint:** `POST /tools/suggest_differentials`

**Input schema:**
```json
{
  "patient_id": "string",
  "abnormal_findings": [
    {
      "analyte": "string",
      "value": "number",
      "unit": "string",
      "direction": "low | high",
      "magnitude": "mild | moderate | severe"
    }
  ],
  "clinical_context": {
    "age_range": "string",
    "sex": "male | female | unspecified",
    "presenting_complaint": "string | null"
  },
  "max_differentials": 5
}
```

**Output schema:**
```json
{
  "patient_id": "string",
  "differentials": [
    {
      "rank": "number",
      "diagnosis": "string",
      "supporting_findings": ["string"],
      "reasoning": "string",
      "confidence": "high | moderate | low",
      "suggested_confirmatory_tests": ["string"]
    }
  ],
  "clinical_caveat": "string"
}
```

**System prompt:**
```
You are a senior clinical consultant reviewing lab results for a medical AI platform.
All patient data is synthetic and de-identified.

Given a set of abnormal laboratory findings and clinical context, suggest differential diagnoses.

Your task:
1. Identify the most clinically plausible diagnoses that explain the pattern of abnormalities.
2. Rank them from most to least likely based on the findings provided.
3. For each differential, cite the specific findings that support it.
4. Suggest 1-3 confirmatory tests that would help narrow the differential.
5. Include a caveat that this is AI-generated and must be reviewed by a qualified clinician.

Use clinical reasoning, not just reference-range logic. Look for patterns across analytes.
For example: thrombocytopenia + microangiopathic anaemia + elevated creatinine should surface TTP/HUS.
Do not anchor to a single abnormal value — consider the full picture.
Respond in valid JSON matching the output schema provided.
Max differentials: as specified in the input (default 5).
```

---

## Synthetic patient fixture index

| ID | Scenario | Panels | Primary differentials |
|---|---|---|---|
| SYN-001 | Sepsis with DIC | CBC, COAG | DIC, bacterial sepsis, TTP |
| SYN-002 | CKD stage 3 | RENAL, CBC | CKD, pre-renal AKI, renovascular |
| SYN-003 | Liver disease | LFT, COAG | Hepatitis, cirrhosis, NAFLD |
| SYN-004 | Iron deficiency anaemia | CBC, IRON | IDA, anaemia of chronic disease, thalassaemia minor |
| SYN-005 | DKA | GLUCOSE, ABG | DKA, lactic acidosis, starvation ketosis |
| SYN-006 | Hyperthyroidism | THYROID, LIPID | Graves, toxic adenoma, subacute thyroiditis |
| SYN-007 | Normal baseline | CBC, RENAL, LFT | No abnormality |
| SYN-008 | Complex mixed picture | CBC, RENAL, COAG | TTP, HUS, SLE with renal involvement |

Fixtures are stored in `/fixtures/synthetic/` as FHIR-aligned JSON. None contain real PHI.

---

## Environment variables

| Variable | Description | Required |
|---|---|---|
| `ANTHROPIC_API_KEY` | Anthropic Claude API key | Yes |
| `MODEL` | Claude model name (default: `claude-sonnet-4-5-20251022`) | No |
| `PORT` | Server port (default: `8000`) | No |
| `ENVIRONMENT` | `development` or `production` | No |

---

## Running locally

```bash
# Install dependencies
pip install fastapi uvicorn anthropic python-dotenv

# Set environment variables
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env

# Run the server
uvicorn main:app --reload --port 8000

# Test tool discovery
curl http://localhost:8000/.well-known/agent.json

# Test a tool call
curl -X POST http://localhost:8000/tools/flag_critical_values \
  -H "Content-Type: application/json" \
  -d @fixtures/synthetic/SYN-001.json
```

---

## Prompt Opinion integration checklist

- [ ] Register at app.promptopinion.ai
- [ ] Read MCP Server onboarding docs
- [ ] Deploy server to Railway/Render with HTTPS
- [ ] Register server URL in Prompt Opinion developer console
- [ ] Verify agent card is discoverable from the platform
- [ ] Verify each tool is invokable from the Prompt Opinion workspace
- [ ] Publish to Marketplace
- [ ] Confirm submission is discoverable by judges

---

## Notes on clinical accuracy

The system prompts in this server encode domain knowledge from Medical Laboratory Science training. Key design decisions:

- The `suggest_differentials` prompt explicitly instructs Claude to look for cross-analyte patterns, not single-value flags. This is what separates it from a rule-based system.
- The `interpret_lab_panel` prompt distinguishes between reference-range status and clinical significance — a value can be mildly abnormal with high clinical significance depending on context.
- Critical value thresholds in `flag_critical_values` follow standard clinical laboratory practice (CLSI EP23 / local lab policy equivalents), not just reference ranges.
- All output includes a clinical caveat. This is not a diagnostic device. It is a decision support tool.

---

*LabLens MCP — built for Agents Assemble 2026*
