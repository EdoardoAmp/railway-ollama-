FROM ollama/ollama:latest

RUN apt-get update && apt-get install -y python3 python3-pip curl && rm -rf /var/lib/apt/lists/*
RUN pip3 install --break-system-packages fastapi uvicorn httpx

WORKDIR /app
COPY start.sh /app/start.sh
COPY proxy.py /app/proxy.py
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]
