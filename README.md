# LabLens MCP

Medical laboratory intelligence MCP server built for the [Agents Assemble — The Healthcare AI Endgame](https://agents-assemble.devpost.com/) hackathon on the Prompt Opinion Marketplace.

Exposes four JSON-first HTTP tools that interpret synthetic patient lab data using AI reasoning. Supports SHARP extension headers for FHIR context propagation across multi-agent call chains.

> All data processed by this server is strictly synthetic. No real Protected Health Information (PHI) is used at any layer.

---

## Tools

| Tool | Type | Description |
|---|---|---|
| `interpret_lab_panel` | LLM | Interprets a structured lab panel with per-analyte commentary and overall assessment |
| `flag_critical_values` | Rule-based | Scans results for critical/abnormal values, returns prioritized alerts |
| `generate_clinical_summary` | LLM | Generates a chart note, referral letter, or patient-facing summary |
| `suggest_differentials` | LLM | Ranks differential diagnoses from a pattern of abnormal findings |

## Endpoints

```
GET  /
GET  /health
GET  /.well-known/agent.json
POST /mcp/initialize
POST /tools/interpret_lab_panel
POST /tools/flag_critical_values
POST /tools/generate_clinical_summary
POST /tools/suggest_differentials
```

---

## LLM providers

Switch providers by setting `LLM_PROVIDER` in `.env`. Only the API key for the active provider is required.

| Provider | `LLM_PROVIDER` value | Default model |
|---|---|---|
| Anthropic Claude | `anthropic` | `claude-sonnet-4-5-20251022` |
| Google Gemini | `gemini` | `gemini-2.0-flash` |
| OpenAI | `openai` | `gpt-4o-mini` |
| Mistral AI | `mistral` | `mistral-small-latest` |

---

## Local setup

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
copy .env.example .env       # then add your API key
uvicorn main:app --reload --port 8000
```

Test the server:

```bash
# Health check
curl http://localhost:8000/health

# Agent card
curl http://localhost:8000/.well-known/agent.json

# Rule-based tool (no API key needed)
curl -X POST http://localhost:8000/tools/flag_critical_values \
  -H "Content-Type: application/json" \
  -d @fixtures/synthetic/SYN-001.json
```

### SHARP context headers (optional)

Pass these on any tool request to propagate FHIR patient context:

```
X-FHIR-Server-URL: https://your-fhir-server/R4
X-FHIR-Access-Token: <bearer token>
X-Patient-ID: SYN-001
```

---

## Environment variables

```bash
# .env.example — copy to .env and fill in your key(s)

LLM_PROVIDER=anthropic          # anthropic | gemini | openai | mistral

ANTHROPIC_API_KEY=...
MODEL=claude-sonnet-4-5-20251022

GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.0-flash

OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o-mini

MISTRAL_API_KEY=...
MISTRAL_MODEL=mistral-small-latest

PORT=8000
ENVIRONMENT=development         # development | production
```

---

## Tests

```bash
pytest
```

## Fixture replay

```bash
python scripts/replay_fixtures.py
```

---

## Synthetic patient fixtures

| ID | Scenario | Primary differentials |
|---|---|---|
| SYN-001 | Sepsis with DIC | DIC, bacterial sepsis, TTP |
| SYN-002 | CKD stage 3 | CKD, pre-renal AKI, renovascular |
| SYN-003 | Liver disease | Hepatitis, cirrhosis, NAFLD |
| SYN-004 | Iron deficiency anaemia | IDA, anaemia of chronic disease, thalassaemia minor |
| SYN-005 | DKA | DKA, lactic acidosis, starvation ketosis |
| SYN-006 | Hyperthyroidism | Graves, toxic adenoma, subacute thyroiditis |
| SYN-007 | Normal baseline | No abnormality |
| SYN-008 | Complex mixed picture | TTP, HUS, SLE with renal involvement |

---

## Deploy (Railway)

Set `ENVIRONMENT=production` and your chosen `LLM_PROVIDER` + API key in Railway environment variables. `PORT` is injected automatically.

---

*Built for Agents Assemble 2026 — Prompt Opinion Marketplace track*
