FROM mcr.microsoft.com/playwright/python:v1.64.1-jammy

WORKDIR /app

# Ensure output is unbuffered
ENV PYTHONUNBUFFERED=1

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps chromium

# Copy source code
COPY . .

# Default port for Render
ENV PORT=10000
EXPOSE 10000

# Start application
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
