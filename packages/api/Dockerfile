FROM python:3.12-slim

WORKDIR /intellect

COPY packages/api/requirements.txt packages/api/requirements.txt
COPY packages/agents/requirements.txt packages/agents/requirements.txt
RUN pip install --no-cache-dir \
    -r packages/api/requirements.txt \
    -r packages/agents/requirements.txt

COPY packages/shared packages/shared
COPY packages/agents packages/agents
RUN pip install --no-cache-dir packages/shared

COPY packages/api packages/api

WORKDIR /intellect/packages/api

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
