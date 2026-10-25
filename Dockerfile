FROM mcr.microsoft.com/playwright/python:v1.64.1-jammy

WORKDIR /app

# Ensure output is unbuffered
ENV PYTHONUNBUFFERED=1

# Install dependencies from service directory
COPY services/douyin-api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps chromium

# Copy application source code from service directory
COPY services/douyin-api/ .

# Default port for Render (Render dynamically sets PORT)
ENV PORT=10000
EXPOSE 10000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Start application
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
