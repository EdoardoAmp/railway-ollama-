from fastapi import FastAPI, Request, Response, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import httpx
import os
import json

# Configuration
OLLAMA_BASE = os.getenv("OLLAMA_INTERNAL_URL", "http://127.0.0.1:11434")
DEFAULT_MODEL = os.getenv("ODYSSEUS_DEFAULT_MODEL", "qwen2.5-coder:7b")
ALLOWED_MODELS_STR = os.getenv("ODYSSEUS_ALLOWED_MODELS", "qwen2.5-coder:7b,llama3.1:8b,llama3.2:3b,codellama:13b")
PRELOAD_MODELS_STR = os.getenv("ODYSSEUS_PRELOAD_MODELS", "qwen2.5-coder:7b")
REQUEST_TIMEOUT = int(os.getenv("ODYSSEUS_REQUEST_TIMEOUT_SECONDS", "180"))
AUTH_TOKEN = os.getenv("ODYSSEUS_LLM_TOKEN", None)

# Parse comma-separated model lists
ALLOWED_MODELS = [m.strip() for m in ALLOWED_MODELS_STR.split(",") if m.strip()]
PRELOAD_MODELS = [m.strip() for m in PRELOAD_MODELS_STR.split(",") if m.strip()]

app = FastAPI(title="Odysseus Local LLM Router")


# Pydantic models for request/response validation
class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = None
    messages: List[Message]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False


class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    owned_by: str = "odysseus-local"


class ModelsListResponse(BaseModel):
    object: str = "list"
    data: List[ModelInfo]


async def get_installed_models() -> List[str]:
    """Fetch installed models from Ollama."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{OLLAMA_BASE}/api/tags")
            if r.status_code == 200:
                data = r.json()
                models = data.get("models", [])
                return [m.get("name", "") for m in models if m.get("name")]
    except Exception as e:
        print(f"Error fetching installed models: {e}")
    return []


def verify_auth(authorization: Optional[str] = Header(None)) -> bool:
    """Verify Bearer token if AUTH_TOKEN is configured."""
    if not AUTH_TOKEN:
        return True
    if not authorization:
        return False
    try:
        scheme, token = authorization.split(" ", 1)
        return scheme.lower() == "bearer" and token == AUTH_TOKEN
    except:
        return False


@app.get("/health")
async def health():
    """Health check endpoint."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{OLLAMA_BASE}/api/tags")
        
        installed = await get_installed_models()
        
        return {
            "status": "ok",
            "ollama": "ok",
            "default_model": DEFAULT_MODEL,
            "allowed_models": ALLOWED_MODELS,
            "loaded_models": installed,
        }
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "ollama": "unreachable",
                "error": str(exc),
            },
        )


@app.get("/api/tags")
async def api_tags():
    """Proxy to Ollama /api/tags."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{OLLAMA_BASE}/api/tags")
        return r.json()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Ollama unreachable: {str(e)}")


@app.get("/v1/models")
async def list_models():
    """OpenAI-compatible model list endpoint."""
    installed = await get_installed_models()
    # Return only allowed models that are installed
    available = [m for m in installed if m in ALLOWED_MODELS]
    
    data = [ModelInfo(id=m) for m in available]
    return ModelsListResponse(data=data)


@app.get("/models/status")
async def models_status():
    """Detailed model status endpoint."""
    installed = await get_installed_models()
    missing = [m for m in ALLOWED_MODELS if m not in installed]
    
    return {
        "default_model": DEFAULT_MODEL,
        "allowed_models": ALLOWED_MODELS,
        "installed_models": installed,
        "missing_models": missing,
        "preload_models": PRELOAD_MODELS,
        "ollama_url": OLLAMA_BASE,
        "provider": "local_odysseus_ollama",
    }


@app.post("/v1/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    authorization: Optional[str] = Header(None),
):
    """OpenAI-compatible chat completions endpoint."""
    
    # Verify authentication if required
    if not verify_auth(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Determine model to use
    model = request.model or DEFAULT_MODEL
    
    # Validate model is allowed
    if model not in ALLOWED_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Model '{model}' not allowed. Allowed models: {', '.join(ALLOWED_MODELS)}",
        )
    
    # Prepare request for Ollama
    payload = {
        "model": model,
        "messages": [{"role": m.role, "content": m.content} for m in request.messages],
        "stream": False,  # Disable streaming for now
    }
    
    if request.temperature is not None:
        payload["temperature"] = request.temperature
    if request.max_tokens is not None:
        payload["max_tokens"] = request.max_tokens
    
    try:
        async with httpx.AsyncClient(timeout=float(REQUEST_TIMEOUT)) as client:
            r = await client.post(
                f"{OLLAMA_BASE}/v1/chat/completions",
                json=payload,
            )
        
        if r.status_code != 200:
            raise HTTPException(
                status_code=r.status_code,
                detail=f"Ollama error: {r.text}",
            )
        
        return r.json()
    
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail=f"Request timeout after {REQUEST_TIMEOUT} seconds",
        )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Ollama error: {str(e)}",
        )


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy(path: str, request: Request):
    """Fallback proxy for unmapped Ollama endpoints."""
    # Skip proxying if path is already handled
    if path in ["health", "api/tags", "v1/models", "models/status", "v1/chat/completions"]:
        return JSONResponse(status_code=404, content={"error": "Not found"})
    
    url = f"{OLLAMA_BASE}/{path}"
    body = await request.body()

    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in {"host", "content-length"}
    }

    try:
        async with httpx.AsyncClient(timeout=float(REQUEST_TIMEOUT)) as client:
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
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Proxy error: {str(e)}")
