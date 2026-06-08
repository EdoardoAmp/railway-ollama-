# Odysseus Local LLM Router

A self-hosted, multi-model local LLM router built on Railway with Ollama and FastAPI.

## Features

- **Multi-model support**: Switch between multiple local models per request
- **OpenAI-compatible API**: Drop-in replacement for OpenAI endpoints
- **Model preloading**: Automatically pull and cache models on startup
- **Health monitoring**: Detailed health and model status endpoints
- **Optional authentication**: Bearer token support for /v1/chat/completions
- **No external APIs**: Fully local, no cloud LLM dependencies

## Environment Variables

### Core Configuration
- `ODYSSEUS_DEFAULT_MODEL` — Default model if not specified in request (default: `qwen2.5-coder:7b`)
- `ODYSSEUS_ALLOWED_MODELS` — Comma-separated list of allowed models (default: `qwen2.5-coder:7b,llama3.1:8b,llama3.2:3b,codellama:13b`)
- `ODYSSEUS_PRELOAD_MODELS` — Comma-separated list of models to pull on startup (default: `qwen2.5-coder:7b`)
- `ODYSSEUS_MODEL_PULL_ON_START` — Pull preload models on startup (default: `false`)

### Performance Tuning
- `ODYSSEUS_KEEP_ALIVE` — Ollama keep-alive timeout (default: `30m`)
- `ODYSSEUS_NUM_PARALLEL` — Parallel model requests (default: `1`)
- `ODYSSEUS_REQUEST_TIMEOUT_SECONDS` — Request timeout in seconds (default: `180`)

### Security
- `ODYSSEUS_LLM_TOKEN` — Optional Bearer token for /v1/chat/completions (default: none)

## Endpoints

### Health & Status
- `GET /health` — Health check with model info
- `GET /api/tags` — Ollama model tags
- `GET /v1/models` — OpenAI-compatible model list
- `GET /models/status` — Detailed model status

### Chat Completions
- `POST /v1/chat/completions` — OpenAI-compatible chat endpoint

## Model Policy

### Default Model
- Default: `qwen2.5-coder:7b`
- Used if request does not specify a model

### Allowed Models
- Only models in `ODYSSEUS_ALLOWED_MODELS` can be used
- If request model is not allowed, returns HTTP 400 with clear error
- Allowed models: `qwen2.5-coder:7b`, `llama3.1:8b`, `llama3.2:3b`, `codellama:13b`

### Preload Models
- Models in `ODYSSEUS_PRELOAD_MODELS` are pulled on startup if `ODYSSEUS_MODEL_PULL_ON_START=true`
- Default preload: `qwen2.5-coder:7b`
- Only preload models listed in this variable; no automatic heavy model pulls

### Missing Models
- Models in `ODYSSEUS_ALLOWED_MODELS` but not installed are listed in `/models/status`
- Missing models are NOT automatically pulled unless explicitly in `ODYSSEUS_PRELOAD_MODELS`

## Example Requests

### List Models
```bash
curl https://odysseus-llm-production.up.railway.app/v1/models
```

### Chat Completion
```bash
curl -X POST https://odysseus-llm-production.up.railway.app/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-coder:7b",
    "messages": [
      {"role": "user", "content": "Hello, who are you?"}
    ],
    "temperature": 0.7,
    "max_tokens": 256
  }'
```

### With Authentication
```bash
curl -X POST https://odysseus-llm-production.up.railway.app/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{...}'
```

### Invalid Model (HTTP 400)
```bash
curl -X POST https://odysseus-llm-production.up.railway.app/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "not-allowed-model",
    "messages": [{"role": "user", "content": "test"}]
  }'
# Returns HTTP 400: Model 'not-allowed-model' not allowed. Allowed models: ...
```

## Deployment

Deployed on Railway with:
- Base image: `ollama/ollama:latest`
- Runtime: FastAPI + Uvicorn
- Ollama internal: `127.0.0.1:11434`
- Public domain: `https://odysseus-llm-production.up.railway.app`

## Supported Models

### Tier 1 (Recommended)
- `qwen2.5-coder:7b` — Code generation, 7B parameters (default)
- `llama3.1:8b` — General purpose, 8B parameters
- `llama3.2:3b` — Lightweight, 3B parameters

### Tier 2 (Heavier)
- `codellama:13b` — Code-focused, 13B parameters

## Architecture

```
Railway Public Domain
        ↓
   FastAPI Router
        ↓
  Model Validation
        ↓
  Ollama (127.0.0.1:11434)
        ↓
   Local Models
```

## No External APIs

This router uses **only local Ollama models**. No external LLM APIs (OpenAI, Anthropic, etc.) are used or supported.

## License

MIT