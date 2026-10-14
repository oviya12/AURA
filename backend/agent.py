import json
from typing import Any, AsyncIterator
from anthropic import AsyncAnthropic
from app.config import get_settings
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.research_tools import TOOL_SCHEMAS, execute_tool

MAX_TOOL_ROUNDS = 6
MAX_TOOL_OUTPUT_CHARS = 18000


def _source_type(tool_name: str) -> str:
    return {
        "search_pubmed": "pubmed",
        "search_openfda_label": "openfda",
        "search_clinical_trials": "clinicaltrials",
    }.get(tool_name, "pubmed")


def _collect_citations(records: list[dict[str, Any]], citations: dict[str, dict[str, Any]]) -> None:
    for record in records:
        identifier, url = record.get("identifier"), record.get("url")
        if not identifier or not url:
            continue
        citations[identifier] = {
            "source_type": record.get("source_type", "pubmed"),
            "title": record.get("title", identifier),
            "url": url,
            "identifier": identifier,
            "citation": record.get("citation", ""),
            "published_date": record.get("published_date") or record.get("effective_time"),
        }


async def run_research_agent(
    prompt: str,
    history: list[dict[str, str]],
    enabled_sources: list[str] | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Manual tool loop using the standard Anthropic Python SDK, not Claude Agent SDK."""
    settings = get_settings()
    if not settings.litellm_api_key:
        raise RuntimeError("LITELLM_API_KEY is missing. Set it in .env.")

    enabled = set(enabled_sources or ["pubmed", "openfda", "clinicaltrials"])
    source_to_tool = {
        "pubmed": "search_pubmed",
        "openfda": "search_openfda_label",
        "clinicaltrials": "search_clinical_trials",
    }
    allowed_names = {source_to_tool[s] for s in enabled if s in source_to_tool}
    tools = [tool for tool in TOOL_SCHEMAS if tool["name"] in allowed_names]

    client = AsyncAnthropic(
        api_key=settings.litellm_api_key,
        base_url=settings.litellm_base_url.rstrip("/"),
        timeout=settings.request_timeout_seconds,
        max_retries=1,
    )
    messages: list[dict[str, Any]] = []
    for turn in history[-8:]:
        if turn.get("role") in {"user", "assistant"} and turn.get("content"):
            messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({
        "role": "user",
        "content": (
            f"Enabled sources for this turn: {', '.join(sorted(enabled)) or 'none'}. "
            "Do not call tools for disabled sources.\n\nCurrent question:\n" + prompt
        ),
    })

    citations: dict[str, dict[str, Any]] = {}
    answer_parts: list[str] = []
    yield {"event": "start", "data": {"model": settings.litellm_model}}

    try:
        for _round in range(MAX_TOOL_ROUNDS):
            response = await client.messages.create(
                model=settings.litellm_model,
                max_tokens=3000,
                system=SYSTEM_PROMPT,
                tools=tools,
                messages=messages,
            )
            assistant_content = []
            tool_uses = []
            for block in response.content:
                if block.type == "text":
                    assistant_content.append({"type": "text", "text": block.text})
                    if block.text:
                        answer_parts.append(block.text)
                        yield {"event": "content", "data": {"text": block.text}}
                elif block.type == "tool_use":
                    assistant_content.append({
                        "type": "tool_use", "id": block.id,
                        "name": block.name, "input": block.input,
                    })
                    tool_uses.append(block)
                    yield {"event": "tool_call", "data": {
                        "tool": block.name, "input": block.input
                    }}

            messages.append({"role": "assistant", "content": assistant_content})
            if not tool_uses or response.stop_reason != "tool_use":
                break

            tool_results = []
            for call in tool_uses:
                records: list[dict[str, Any]] = []
                try:
                    records = await execute_tool(call.name, dict(call.input or {}))
                    _collect_citations(records, citations)
                    result_text = json.dumps(
                        {"source": _source_type(call.name), "results": records},
                        ensure_ascii=False,
                    )
                except Exception as exc:
                    result_text = json.dumps({
                        "error": f"Tool failed: {type(exc).__name__}", "results": []
                    })
                if len(result_text) > MAX_TOOL_OUTPUT_CHARS:
                    result_text = result_text[:MAX_TOOL_OUTPUT_CHARS] + "\n[Tool output truncated]"
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": call.id,
                    "content": result_text,
                })
                yield {"event": "tool_result", "data": {
                    "tool": call.name, "result_count": len(records)
                }}
            messages.append({"role": "user", "content": tool_results})
        else:
            messages.append({"role": "user", "content":
                "You reached the research tool-call limit. Answer using only retrieved evidence and state limitations."})
            final_response = await client.messages.create(
                model=settings.litellm_model,
                max_tokens=2000,
                system=SYSTEM_PROMPT,
                tools=tools,
                messages=messages,
            )
            for block in final_response.content:
                if block.type == "text" and block.text:
                    answer_parts.append(block.text)
                    yield {"event": "content", "data": {"text": block.text}}
    finally:
        await client.close()

    answer = "\n".join(part.strip() for part in answer_parts if part.strip()).strip()
    citation_list = list(citations.values())
    yield {"event": "citations", "data": {"citations": citation_list}}
    yield {"event": "complete", "data": {"answer": answer, "citations": citation_list}}
