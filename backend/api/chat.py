import asyncio
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from app.schemas import ChatRequest
from app.state import get_or_create_conversation, get_history, add_turn, list_conversations
from app.agent.research_agent import run_research_agent

router = APIRouter()


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/chat/stream")
async def chat_stream(body: ChatRequest):
    conversation_id = get_or_create_conversation(body.conversation_id)
    history = get_history(conversation_id)
    # Make source toggles explicit to the agent. Disabled sources must not be called.
    enabled = [name for name, is_on in body.sources.model_dump().items() if is_on]
    if not enabled:
        raise HTTPException(status_code=400, detail="Enable at least one research source.")
    source_instruction = (
        f"Only use these research sources for this turn: {', '.join(enabled)}. "
        "Do not call tools for disabled sources."
    )
    prompt = f"{source_instruction}\n\n{body.message}"

    async def stream():
        answer = ""
        try:
            yield _sse("conversation", {"conversation_id": conversation_id})
            async for item in run_research_agent(prompt, history, enabled):
                if item["event"] == "content":
                    answer += item["data"].get("text", "")
                yield _sse(item["event"], item["data"])
            add_turn(conversation_id, "user", body.message)
            add_turn(conversation_id, "assistant", answer)
        except Exception as exc:
            # Do not leak secrets or full stack traces to the browser.
            yield _sse("error", {
                "message": "The research agent failed. Check the backend terminal logs and proxy configuration.",
                "error_type": type(exc).__name__,
            })

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/conversations")
async def conversations():
    return {"conversations": list_conversations()}


@router.get("/conversations/{conversation_id}")
async def conversation_detail(conversation_id: str):
    history = get_history(conversation_id)
    if not history:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return {"conversation_id": conversation_id, "messages": history}
