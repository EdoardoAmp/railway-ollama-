from fastapi import FastAPI, Request, Response
import httpx
import os

OLLAMA_BASE = os.getenv("OLLAMA_INTERNAL_URL", "http://127.0.0.1:11434")

app = FastAPI(title="Odysseus Local LLM Proxy")


@app.get("/health")
async def health():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{OLLAMA_BASE}/api/tags")
        return {
            "status": "ok",
            "ollama": "reachable",
            "models": r.json().get("models", []),
        }
    except Exception as exc:
        return {
            "status": "degraded",
            "ollama": "unreachable",
            "error": exc.__class__.__name__,
        }


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy(path: str, request: Request):
    url = f"{OLLAMA_BASE}/{path}"
    body = await request.body()

    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in {"host", "content-length"}
    }

    async with httpx.AsyncClient(timeout=300.0) as client:
        upstream = await client.request(
            request.method,
            url,
            content=body,
            headers=headers,
            params=request.query_params,
        )

    response_headers = {
        key: value
        for key, value in upstream.headers.items()
        if key.lower() not in {"content-encoding", "transfer-encoding", "connection"}
    }

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
        media_type=upstream.headers.get("content-type"),
    )
