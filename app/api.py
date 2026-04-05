import json
import logging

from fastapi import APIRouter, Depends, Request

from app.dependencies import get_epic_oauth_service, get_tool_service
from app.agent_card import AGENT_CARD
from app.services.epic_oauth_service import EPIC_SANDBOX_PATIENT_IDS
from app.sharp import SharpContext, extract_sharp_context
from app.models.tools import (
    FlagCriticalValuesRequest,
    FlagCriticalValuesResponse,
    GenerateClinicalSummaryRequest,
    GenerateClinicalSummaryResponse,
    InterpretLabPanelRequest,
    InterpretLabPanelResponse,
    SuggestDifferentialsRequest,
    SuggestDifferentialsResponse,
)
from app.services.tool_service import ToolService

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# MCP tool definitions — served via tools/list
# ---------------------------------------------------------------------------

_MCP_TOOLS = [
    {
        "name": "flag_critical_values",
        "description": (
            "Scans lab results for critical and abnormal values. Returns a prioritized alert list "
            "sorted by severity. Rule-based — no LLM required. Accepts SHARP headers to pull live "
            "FHIR Observation data automatically."
        ),
        "inputSchema": FlagCriticalValuesRequest.model_json_schema(),
    },
    {
        "name": "interpret_lab_panel",
        "description": (
            "Interprets a structured lab panel using AI reasoning. Returns per-analyte commentary "
            "with clinical context and significance, plus an overall assessment and recommended actions."
        ),
        "inputSchema": InterpretLabPanelRequest.model_json_schema(),
    },
    {
        "name": "generate_clinical_summary",
        "description": (
            "Generates a clinical narrative from lab results. Supports chart_note, referral, and "
            "patient_facing summary types. Reduces documentation burden on clinicians."
        ),
        "inputSchema": GenerateClinicalSummaryRequest.model_json_schema(),
    },
    {
        "name": "suggest_differentials",
        "description": (
            "Ranks differential diagnoses from a pattern of abnormal lab findings using clinical "
            "reasoning across analytes. Surfaces cross-analyte patterns that rule-based systems miss."
        ),
        "inputSchema": SuggestDifferentialsRequest.model_json_schema(),
    },
]


def _dispatch_tool(
    tool_name: str,
    arguments: dict,
    tool_service: ToolService,
    sharp: SharpContext,
) -> dict:
    if tool_name == "flag_critical_values":
        return tool_service.flag_critical_values(
            FlagCriticalValuesRequest.model_validate(arguments), sharp=sharp
        ).model_dump()
    if tool_name == "interpret_lab_panel":
        return tool_service.interpret_lab_panel(
            InterpretLabPanelRequest.model_validate(arguments), sharp=sharp
        ).model_dump()
    if tool_name == "generate_clinical_summary":
        return tool_service.generate_clinical_summary(
            GenerateClinicalSummaryRequest.model_validate(arguments), sharp=sharp
        ).model_dump()
    if tool_name == "suggest_differentials":
        return tool_service.suggest_differentials(
            SuggestDifferentialsRequest.model_validate(arguments), sharp=sharp
        ).model_dump()
    raise ValueError(f"Unknown tool: {tool_name}")


# ---------------------------------------------------------------------------
# Health / discovery
# ---------------------------------------------------------------------------

@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/.well-known/agent.json")
def agent_card() -> dict:
    return AGENT_CARD


# ---------------------------------------------------------------------------
# MCP initialize — advertises SHARP capabilities to the calling platform.
#
# Clients (e.g. Prompt Opinion) POST to this endpoint during session setup.
# The response declares that this server understands SHARP context headers
# and will propagate them through every tool invocation.
# ---------------------------------------------------------------------------

@router.post("/mcp/initialize")
def mcp_initialize() -> dict:
    return {
        "protocolVersion": "2024-11-05",
        "serverInfo": {
            "name": AGENT_CARD["name"],
            "version": AGENT_CARD["version"],
        },
        "capabilities": {
            "tools": {"listChanged": False},
            "experimental": AGENT_CARD["capabilities"]["experimental"],
        },
    }


@router.post("/mcp")
async def mcp_jsonrpc(
    request: Request,
    tool_service: ToolService = Depends(get_tool_service),
    sharp: SharpContext = Depends(extract_sharp_context),
) -> dict:
    """MCP Streamable HTTP JSON-RPC endpoint.

    Handles initialize, tools/list, and tools/call messages from
    Prompt Opinion and other MCP-compatible platforms.
    """
    try:
        body = await request.json()
    except Exception:
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}

    method = body.get("method", "")
    req_id = body.get("id")
    params = body.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": AGENT_CARD["name"], "version": AGENT_CARD["version"]},
                "capabilities": {
                    "tools": {"listChanged": False},
                    "experimental": AGENT_CARD["capabilities"]["experimental"],
                },
            },
        }

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": _MCP_TOOLS}}

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        try:
            result = _dispatch_tool(tool_name, arguments, tool_service, sharp)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(result)}]},
            }
        except Exception as exc:
            logger.exception("mcp_tools_call_failed tool=%s", tool_name)
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32000, "message": str(exc)}}

    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}


@router.get("/fhir/epic/patients")
def epic_sandbox_patients() -> dict:
    """Known Epic sandbox patient IDs for developer reference."""
    return {"patients": EPIC_SANDBOX_PATIENT_IDS}


@router.get("/jwks.json")
def jwks(epic_service=Depends(get_epic_oauth_service)) -> dict:
    """Public JWK Set for Epic FHIR JWT assertion verification.

    Register https://<host>/jwks.json as the 'Non-Production JWK Set URL'
    in the Epic developer portal. Epic fetches this to verify tokens.
    Returns an empty keys array when Epic is not configured.
    """
    if not epic_service or not epic_service._settings.epic_private_key:
        return {"keys": []}
    try:
        return {"keys": [epic_service._get_public_jwk()]}
    except Exception:
        logger.warning("jwks_derivation_failed", exc_info=True)
        return {"keys": []}


# ---------------------------------------------------------------------------
# Tool endpoints — all accept optional SHARP context headers.
# ---------------------------------------------------------------------------

@router.post("/tools/flag_critical_values", response_model=FlagCriticalValuesResponse)
def flag_critical_values(
    request: FlagCriticalValuesRequest,
    tool_service: ToolService = Depends(get_tool_service),
    sharp: SharpContext = Depends(extract_sharp_context),
) -> FlagCriticalValuesResponse:
    return tool_service.flag_critical_values(request, sharp=sharp)


@router.post("/tools/interpret_lab_panel", response_model=InterpretLabPanelResponse)
def interpret_lab_panel(
    request: InterpretLabPanelRequest,
    tool_service: ToolService = Depends(get_tool_service),
    sharp: SharpContext = Depends(extract_sharp_context),
) -> InterpretLabPanelResponse:
    return tool_service.interpret_lab_panel(request, sharp=sharp)


@router.post("/tools/generate_clinical_summary", response_model=GenerateClinicalSummaryResponse)
def generate_clinical_summary(
    request: GenerateClinicalSummaryRequest,
    tool_service: ToolService = Depends(get_tool_service),
    sharp: SharpContext = Depends(extract_sharp_context),
) -> GenerateClinicalSummaryResponse:
    return tool_service.generate_clinical_summary(request, sharp=sharp)


@router.post("/tools/suggest_differentials", response_model=SuggestDifferentialsResponse)
def suggest_differentials(
    request: SuggestDifferentialsRequest,
    tool_service: ToolService = Depends(get_tool_service),
    sharp: SharpContext = Depends(extract_sharp_context),
) -> SuggestDifferentialsResponse:
    return tool_service.suggest_differentials(request, sharp=sharp)
