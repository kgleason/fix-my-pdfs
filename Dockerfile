# ============================================================================
# Dockerfile - Docker Container (Optional)
# ============================================================================
FROM python:3.11-slim

# Install system dependencies including Tesseract OCR
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    tesseract-ocr \
    tesseract-ocr-eng \
    ghostscript \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/app.py .
COPY src/models.py .
COPY src/pdf_tagger.py .
COPY src/utils.py .
COPY src/views.py .
COPY src/gunicorn_config.py .

# Copy templates directory
COPY templates/ ./templates/
COPY static/ ./static/

# Create necessary directories
RUN mkdir -p uploads outputs tmp job_tracking

# Expose port
EXPOSE 8880

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8880/', timeout=5)" || exit 1

# Run gunicorn
CMD ["gunicorn", "--config", "gunicorn_config.py", "app:app"]