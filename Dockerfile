# ============================================================================
# Dockerfile - Docker Container (Optional)
# ============================================================================
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY models.py .
COPY pdf_tagger.py .
COPY utils.py .
COPY views.py .
COPY gunicorn_config.py .

# Copy templates directory
COPY templates/ ./templates/

# Create necessary directories
RUN mkdir -p uploads outputs tmp

# Expose port
EXPOSE 8000

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/', timeout=5)" || exit 1

# Run gunicorn
CMD ["gunicorn", "--config", "gunicorn_config.py", "app:app"]