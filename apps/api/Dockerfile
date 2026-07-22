FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ libc6-dev libpq-dev libpango-1.0-0 libpangoft2-1.0-0 libpangocairo-1.0-0 libcairo2 libffi-dev libgdk-pixbuf-2.0-0 libgobject-2.0-0 shared-mime-info && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY apps/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY apps/api .

# Copy database package (monorepo dependency) to /app/packages/database
COPY packages/database ./packages/database

ENV PYTHONPATH="/app"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import httpx; r = httpx.get('http://localhost:8000/health'); r.raise_for_status()"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
