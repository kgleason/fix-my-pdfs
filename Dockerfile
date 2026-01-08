# ============================================================================
# Dockerfile - Docker Container (Optional)
# ============================================================================
FROM python:3.13-slim

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
COPY . .

# Create necessary directories
RUN mkdir -p uploads outputs tmp

# Expose port
EXPOSE 8001

# Run gunicorn
CMD ["gunicorn", "--config", "gunicorn_config.py", "app:app"]
