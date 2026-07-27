# ── Runtime ────────────────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (layer caching)
COPY scripts/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent source
COPY scripts/ .

# ── Runtime config ─────────────────────────────────────────────────────────────
EXPOSE 8000

# Environment variables (set these in Azure App Service / Container App settings)
# GEMINI_API_KEY      — your Gemini API key
# SYSTEM_ACCESSTOKEN  — Azure DevOps PAT with Code (Read) + PR Threads (Write)
# WEBHOOK_SECRET      — optional shared secret from service hook config

CMD ["uvicorn", "webhook_server:app", "--host", "0.0.0.0", "--port", "8000"]
