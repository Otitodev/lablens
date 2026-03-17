# LabLens MCP

LabLens MCP is a FastAPI-based medical laboratory intelligence server built for the Prompt Opinion Marketplace hackathon track. It exposes four JSON-first HTTP tools backed by deterministic validation and Anthropic Claude reasoning for synthetic patient laboratory scenarios.

## Endpoints

- `GET /`
- `GET /health`
- `GET /.well-known/agent.json`
- `POST /tools/interpret_lab_panel`
- `POST /tools/flag_critical_values`
- `POST /tools/generate_clinical_summary`
- `POST /tools/suggest_differentials`

## Local setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn main:app --reload --port 8000
```

## Tests

```bash
pytest
```

## Fixture replay

```bash
python scripts/replay_fixtures.py
```
