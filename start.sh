#!/usr/bin/env sh
set -eu

export OLLAMA_HOST=127.0.0.1:11434
export OLLAMA_KEEP_ALIVE="${ODYSSEUS_KEEP_ALIVE:-30m}"
export OLLAMA_NUM_PARALLEL="${ODYSSEUS_NUM_PARALLEL:-1}"

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

# Preload models if enabled
if [ "${ODYSSEUS_MODEL_PULL_ON_START:-false}" = "true" ]; then
  PRELOAD_MODELS="${ODYSSEUS_PRELOAD_MODELS:-}"
  if [ -n "$PRELOAD_MODELS" ]; then
    echo "Preloading models: $PRELOAD_MODELS"
    IFS=',' read -ra MODELS <<< "$PRELOAD_MODELS"
    for model in "${MODELS[@]}"; do
      model=$(echo "$model" | xargs)  # trim whitespace
      if [ -n "$model" ]; then
        echo "Pulling model: $model"
        ollama pull "$model" || echo "WARNING: Failed to pull $model; continuing"
      fi
    done
  fi
fi

echo "Starting HTTP proxy on Railway PORT=${PORT:-8080}"
exec uvicorn proxy:app --host 0.0.0.0 --port "${PORT:-8080}"
