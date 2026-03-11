FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    swi-prolog \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY forge/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY forge/ ./forge/
COPY mrs/ ./mrs/
COPY ledger/ ./ledger/

WORKDIR /app/forge

EXPOSE 8765

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8765"]
