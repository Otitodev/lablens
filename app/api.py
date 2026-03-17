from fastapi import APIRouter, Depends

from app.dependencies import get_tool_service
from app.agent_card import AGENT_CARD
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

router = APIRouter()


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
