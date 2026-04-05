# LabLens MCP

Medical laboratory intelligence MCP server built for the [Agents Assemble — The Healthcare AI Endgame](https://agents-assemble.devpost.com/) hackathon on the Prompt Opinion Marketplace.

Exposes four JSON-first HTTP tools that interpret patient lab data using AI reasoning. Supports SHARP Extension Specs for FHIR context propagation across multi-agent call chains, and integrates with Epic's FHIR sandbox via OAuth 2.0 JWT assertion.

> All data processed by this server is strictly synthetic and de-identified. No real Protected Health Information (PHI) is used at any layer.

**Live:** `https://lablens.up.railway.app`

---

## Tools

| Tool | Type | Description |
|---|---|---|
| `interpret_lab_panel` | LLM | Interprets a structured lab panel with per-analyte commentary and overall assessment |
| `flag_critical_values` | Rule-based | Scans results for critical/abnormal values and returns a prioritized alert list |
| `generate_clinical_summary` | LLM | Generates a chart note, referral letter, or patient-facing summary |
| `suggest_differentials` | LLM | Ranks differential diagnoses from a pattern of abnormal findings |

## Endpoints

```
GET  /health
GET  /.well-known/agent.json
GET  /jwks.json
POST /mcp/initialize
POST /tools/interpret_lab_panel
POST /tools/flag_critical_values
POST /tools/generate_clinical_summary
POST /tools/suggest_differentials
GET  /fhir/epic/patients
```

---

## LLM providers

Switch providers by setting `LLM_PROVIDER` in `.env`. Only the API key for the active provider is required.

| Provider | `LLM_PROVIDER` | Default model |
|---|---|---|
| Anthropic Claude | `anthropic` | `claude-sonnet-4-5-20251022` |
| Google Gemini | `gemini` | `gemini-2.0-flash` |
| OpenAI | `openai` | `gpt-4o-mini` |
| Mistral AI | `mistral` | `mistral-small-latest` |

---

## SHARP Extension Specs

All tool endpoints accept [SHARP](https://www.sharponmcp.com) context headers for FHIR patient context propagation:

```
X-FHIR-Server-URL: https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4
X-FHIR-Access-Token: <bearer token>
X-Patient-ID: <patient id>
```

When SHARP headers are present, LabLens automatically fetches live lab Observations from the FHIR server and passes them to the AI tools. When absent, tools operate on the request body (synthetic data).

SHARP capabilities are declared on `POST /mcp/initialize` and discoverable via the agent card.

---

## Epic FHIR Integration

LabLens integrates with Epic's FHIR R4 sandbox using the **Backend Systems OAuth 2.0** flow (JWT assertion / `private_key_jwt`).

**How it works:**
1. An RSA 2048-bit key pair is generated with `python scripts/generate_epic_keys.py`
2. The public key is served at `GET /jwks.json` for Epic to verify signatures
3. On each tool call, LabLens auto-fetches an access token by signing a JWT with the private key (RS384) and posting it to Epic's token endpoint
4. The token is cached in memory until expiry

**Setup:**
```bash
python scripts/generate_epic_keys.py
# Copy EPIC_PRIVATE_KEY and EPIC_KID output into .env
# Register app at fhir.epic.com — set Non-Production JWK Set URL to:
# https://lablens.up.railway.app/jwks.json
# Add EPIC_CLIENT_ID from the portal to .env
```

**Epic sandbox patients:**

| Patient ID | Name | Notes |
|---|---|---|
| `eD5PmS3L3BFwWuAnV2bAk2g3` | Camila Lopez | Adult female |
| `erXuFYUfucBZaryVksYEcMg3` | Derrick Lin | Adult male |
| `eq081-VQEgP8drUUqCWzHfw3` | Jason Argonaut | SMART tutorial patient |
| `eIXesllypH3M9tAA5WdJftQ3` | Nancy Smart | Paediatric |

---

## Local setup

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
copy .env.example .env       # then fill in your key(s)
uvicorn main:app --reload --port 8000
```

Quick tests:

```bash
# Health check
curl http://localhost:8000/health

# SHARP capability declaration
curl -X POST http://localhost:8000/mcp/initialize

# Public key (for Epic JWK registration)
curl http://localhost:8000/jwks.json

# Rule-based tool — no LLM key needed
curl -X POST http://localhost:8000/tools/flag_critical_values \
  -H "Content-Type: application/json" \
  -d @fixtures/synthetic/SYN-001.json

# LLM tool with SHARP + Epic FHIR context
curl -X POST http://localhost:8000/tools/flag_critical_values \
  -H "Content-Type: application/json" \
  -H "X-FHIR-Server-URL: https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4" \
  -H "X-Patient-ID: eq081-VQEgP8drUUqCWzHfw3" \
  -d '{"patient_id":"eq081-VQEgP8drUUqCWzHfw3","results":{}}'
```

---

## Environment variables

```bash
# LLM provider (one key required)
LLM_PROVIDER=openai          # anthropic | gemini | openai | mistral

ANTHROPIC_API_KEY=...
MODEL=claude-sonnet-4-5-20251022

GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.0-flash

OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o-mini

MISTRAL_API_KEY=...
MISTRAL_MODEL=mistral-small-latest

# Epic FHIR (optional — enables live FHIR data from Epic sandbox)
EPIC_CLIENT_ID=...
EPIC_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n
EPIC_KID=lablens-1

PORT=8000
ENVIRONMENT=development      # development | production
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

Set `ENVIRONMENT=production`, your chosen `LLM_PROVIDER` + API key, and optionally the Epic variables in Railway environment variables. `PORT` is injected automatically.

---

*Built for Agents Assemble 2026 — Prompt Opinion Marketplace track*
