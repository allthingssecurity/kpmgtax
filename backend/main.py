import json
import os
from contextlib import asynccontextmanager

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

load_dotenv()

from agents.graph import create_graph
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from agents.prompts import SYSTEM_PROMPT

graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph
    graph = create_graph()
    yield


app = FastAPI(title="KPMG AI - Tax Law Research", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


@app.post("/chat")
async def chat(req: ChatRequest):
    async def event_stream():
        messages = [SystemMessage(content=SYSTEM_PROMPT)]
        for msg in req.history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        messages.append(HumanMessage(content=req.message))

        full_response = ""
        try:
            async for event in graph.astream_events(
                {"messages": messages},
                version="v2",
            ):
                kind = event["event"]

                # Tool call started
                if kind == "on_tool_start":
                    tool_name = event.get("name", "unknown")
                    tool_input = event.get("data", {}).get("input", {})
                    query = ""
                    if isinstance(tool_input, dict):
                        query = tool_input.get("query", tool_input.get("section", str(tool_input)))
                    elif isinstance(tool_input, str):
                        query = tool_input
                    yield {
                        "event": "trace",
                        "data": json.dumps({
                            "type": "tool_start",
                            "tool": tool_name,
                            "query": str(query)[:200],
                        }),
                    }

                # Tool call finished
                elif kind == "on_tool_end":
                    tool_name = event.get("name", "unknown")
                    output = event.get("data", {}).get("output", "")
                    if hasattr(output, "content"):
                        output = output.content
                    output_str = str(output)[:500]
                    yield {
                        "event": "trace",
                        "data": json.dumps({
                            "type": "tool_end",
                            "tool": tool_name,
                            "result_preview": output_str,
                        }),
                    }

                # LLM streaming tokens
                elif kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        # Only stream text content, not tool call fragments
                        if isinstance(chunk.content, str):
                            full_response += chunk.content
                            yield {
                                "event": "token",
                                "data": json.dumps({"content": chunk.content}),
                            }

            yield {
                "event": "done",
                "data": json.dumps({"full_response": full_response}),
            }
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}),
            }

    return EventSourceResponse(event_stream())


@app.get("/health")
async def health():
    return {"status": "ok", "service": "KPMG AI"}


@app.get("/")
async def serve_frontend():
    return FileResponse(FRONTEND_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
