from typing import Any
from app.services.pubmed import search_pubmed
from app.services.openfda import search_openfda
from app.services.clinicaltrials import search_clinical_trials

TOOL_SCHEMAS = [
    {
        "name": "search_pubmed",
        "description": "Search PubMed biomedical literature. Returns metadata, abstracts, URLs and PMID citations.",
        "input_schema": {"type": "object", "properties": {
            "query": {"type": "string", "description": "Biomedical search query."},
            "limit": {"type": "integer", "description": "Number of records (1-10).", "minimum": 1, "maximum": 10}},
            "required": ["query"]},
    },
    {
        "name": "search_openfda_label",
        "description": "Search official openFDA drug labels for indications, warnings, contraindications, dosage label text and adverse reactions. Not personalized dosing advice.",
        "input_schema": {"type": "object", "properties": {
            "drug_name": {"type": "string", "description": "Drug generic or brand name."},
            "limit": {"type": "integer", "description": "Number of label records (1-5).", "minimum": 1, "maximum": 5}},
            "required": ["drug_name"]},
    },
    {
        "name": "search_clinical_trials",
        "description": "Search ClinicalTrials.gov for registered studies, design, phase, recruitment status, dates, outcomes and NCT identifiers.",
        "input_schema": {"type": "object", "properties": {
            "query": {"type": "string", "description": "Condition, intervention, or trial terms."},
            "limit": {"type": "integer", "description": "Number of trials (1-10).", "minimum": 1, "maximum": 10}},
            "required": ["query"]},
    },
]


async def execute_tool(name: str, arguments: dict[str, Any]) -> list[dict[str, Any]]:
    if name == "search_pubmed":
        return await search_pubmed(arguments["query"], arguments.get("limit", 5))
    if name == "search_openfda_label":
        return await search_openfda(arguments["drug_name"], arguments.get("limit", 3))
    if name == "search_clinical_trials":
        return await search_clinical_trials(arguments["query"], arguments.get("limit", 5))
    raise ValueError(f"Unknown tool: {name}")
