#!/usr/bin/env sh
set -eu

export OLLAMA_HOST=127.0.0.1:11434
export OLLAMA_KEEP_ALIVE="${OLLAMA_KEEP_ALIVE:-30m}"
export OLLAMA_NUM_PARALLEL="${OLLAMA_NUM_PARALLEL:-1}"

echo "Starting Ollama internally on ${OLLAMA_HOST}"
ollama serve &
OLLAMA_PID=$!

echo "Waiting for Ollama..."
for i in $(seq 1 120); do
  if curl -sS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    echo "Ollama is ready"
    break
  fi
  sleep 1
done

if ! curl -sS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  echo "ERROR: Ollama did not become ready"
  exit 1
fi

if [ -n "${ODYSSEUS_DEFAULT_MODEL:-}" ]; then
  echo "Pulling default model: ${ODYSSEUS_DEFAULT_MODEL}"
  ollama pull "${ODYSSEUS_DEFAULT_MODEL}" || echo "WARNING: model pull failed; service will still start"
fi

echo "Starting HTTP proxy on Railway PORT=${PORT}"
exec uvicorn proxy:app --host 0.0.0.0 --port "${PORT}"
