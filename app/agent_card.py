AGENT_CARD = {
    "name": "LabLens MCP",
    "description": (
        "Medical laboratory intelligence server. Interprets lab panels, flags critical "
        "values, generates clinical summaries, and suggests differential diagnoses from "
        "abnormal result patterns."
    ),
    "version": "1.0.0",
    "protocol": "mcp",
    "transport": ["http", "sse"],
    "author": "Otito",
    "contact": "otito.site",
    "data_policy": "synthetic_only",
    "phi": False,
    "tools": [
        "interpret_lab_panel",
        "flag_critical_values",
        "generate_clinical_summary",
        "suggest_differentials",
    ],
    "capabilities": {
        "experimental": {
            # SHARP Extension Spec — https://www.sharponmcp.com
            # fhir_context_required is false because this server operates on
            # synthetic data. SHARP headers are accepted and propagated when
            # provided, enabling seamless integration with live FHIR sessions
            # on the Prompt Opinion platform.
            "sharp": {
                "version": "1.0",
                "fhir_context_required": False,
                "context_headers": [
                    "X-FHIR-Server-URL",
                    "X-FHIR-Access-Token",
                    "X-Patient-ID",
                ],
                "spec_url": "https://www.sharponmcp.com",
            }
        }
    },
}
