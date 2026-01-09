# PDF Autotagger

## *DISCLAIMER*
This software DOES NOT create fully compliant PDFs. It is intended to take care some of the more menial tasks.

## Project Structure

Ensure you have these files:
```
pdf-tagger/
├── app.py              # Main application entry point
├── models.py           # Data models
├── pdf_tagger.py       # Core PDF processing
├── utils.py            # Utility functions
├── views.py            # Flask routes
├── requirements.txt    # Python dependencies
├── gunicorn_config.py  # Gunicorn configuration
├── Dockerfile          # Docker build instructions
├── docker-compose.yml  # Docker Compose config
├── .dockerignore       # Docker ignore patterns
├── test_import.py      # Import test script
└── templates/
    └── index.html      # Frontend template
```

## Pre-flight Check

Before building, install system dependencies for OCR:

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng ghostscript
```

**macOS:**
```bash
brew install tesseract ghostscript
```

**Windows:**
Download and install:
- Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
- Ghostscript: https://www.ghostscript.com/download/gsdnld.html


```bash
# Test imports
python test_import.py

# Expected output:
# ✓ All imports successful!
```

## Quick Start (Development)

```bash
# Install dependencies
pip install -r requirements.txt

# Run with Flask development server
python app.py

# Access at http://localhost:5000
```

## Docker Deployment (Recommended)

### Method 1: Docker Build and Run

```bash
# 1. Build the image
docker build -t pdf-tagger .

# 2. Run the container
docker run -d \
  --name pdf-tagger \
  -p 8000:8000 \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/outputs:/app/outputs \
  -v $(pwd)/tmp:/app/tmp \
  -e SECRET_KEY="your-secret-key-here" \
  pdf-tagger

# 3. Check logs
docker logs -f pdf-tagger

# 4. Access at http://localhost:8000
```

### Method 2: Docker Compose (Easier)

```bash
# 1. Start services
docker-compose up -d

# 2. View logs
docker-compose logs -f

# 3. Stop services
docker-compose down

# 4. Rebuild after changes
docker-compose up -d --build
```

### Troubleshooting Docker

**If container fails to start:**
```bash
# Check container logs
docker logs pdf-tagger

# Run interactively to debug
docker run -it --rm pdf-tagger /bin/bash

# Inside container, test manually:
python -c "from app import app; print(app)"
gunicorn --bind 0.0.0.0:8000 app:app
```

**If imports fail:**
```bash
# Check if all files are in the container
docker run --rm pdf-tagger ls -la

# Verify Python can find modules
docker run --rm pdf-tagger python test_import.py
```

**Port already in use:**
```bash
# Find what's using port 8000
sudo lsof -i :8000
# Or use a different port
docker run -p 8080:8000 pdf-tagger
```

## Production Deployment with Gunicorn (No Docker)

### Method 1: Direct Gunicorn

```bash
# Install dependencies
pip install -r requirements.txt

# Run with default gunicorn settings
gunicorn --bind 0.0.0.0:8000 --workers 4 --threads 2 --timeout 300 app:app

# Or use the configuration file
gunicorn --config gunicorn_config.py app:app

# Or use the start script
chmod +x start.sh
./start.sh
```

### Method 2: Systemd Service (Recommended for Linux servers)

```bash
# 1. Copy your application to /opt/pdf-tagger (or your preferred location)
sudo cp -r . /opt/pdf-tagger

# 2. Create virtual environment
cd /opt/pdf-tagger
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Create .env file
cp .env.example .env
# Edit .env with your settings
nano .env

# 4. Install systemd service
sudo cp pdf-tagger.service /etc/systemd/system/
# Edit the service file paths
sudo nano /etc/systemd/system/pdf-tagger.service

# 5. Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable pdf-tagger
sudo systemctl start pdf-tagger

# 6. Check status
sudo systemctl status pdf-tagger

# View logs
sudo journalctl -u pdf-tagger -f
```

### Method 3: Nginx Reverse Proxy (Production recommended)

```bash
# 1. Install Nginx
sudo apt-get install nginx

# 2. Copy nginx configuration
sudo cp nginx.conf /etc/nginx/sites-available/pdf-tagger
sudo ln -s /etc/nginx/sites-available/pdf-tagger /etc/nginx/sites-enabled/

# 3. Test and reload Nginx
sudo nginx -t
sudo systemctl reload nginx
```

## Environment Variables

Create a `.env` file:

```
SECRET_KEY=your-random-secret-key-here
FLASK_ENV=production
MAX_CONTENT_LENGTH=52428800
```

## Docker Commands Cheat Sheet

```bash
# Build image
docker build -t pdf-tagger .

# Run container
docker run -d -p 8000:8000 --name pdf-tagger pdf-tagger

# View logs
docker logs -f pdf-tagger

# Stop container
docker stop pdf-tagger

# Start container
docker start pdf-tagger

# Remove container
docker rm pdf-tagger

# Remove image
docker rmi pdf-tagger

# Execute command in running container
docker exec -it pdf-tagger /bin/bash

# View container stats
docker stats pdf-tagger

# Inspect container
docker inspect pdf-tagger
```

## Monitoring

```bash
# Check application logs (Docker)
docker logs -f pdf-tagger

# Check application logs (Systemd)
sudo journalctl -u pdf-tagger -f

# Check Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Check gunicorn workers
ps aux | grep gunicorn
```

## Performance Tuning

- **Workers**: `(2 * CPU_cores) + 1`
- **Threads**: 2-4 per worker
- **Timeout**: 300 seconds (for large PDFs)
- **Max requests**: 1000 (restart workers to prevent memory leaks)

## Security Considerations

1. Change SECRET_KEY in production
2. Use HTTPS (Let's Encrypt)
3. Set appropriate file permissions
4. Use firewall rules
5. Regularly update dependencies
6. Monitor disk space (uploads/outputs folders)
7. Limit file upload sizes
8. Run as non-root user in Docker

## Troubleshooting

**"Failed to find attribute 'app' in 'app'":**
```bash
# Test imports
python test_import.py

# Verify app object exists
python -c "from app import app; print(type(app))"
```

**Port already in use:**
```bash
sudo lsof -i :8000
sudo kill <PID>
```

**Permission errors:**
```bash
sudo chown -R www-data:www-data /opt/pdf-tagger
sudo chmod -R 755 /opt/pdf-tagger
```

**Memory issues:**
Reduce number of workers or increase server RAM

**Docker build fails:**
```bash
# Clean up and rebuild
docker system prune -a
docker build --no-cache -t pdf-tagger .
```

## Production Checklist

- [ ] SECRET_KEY is set to a random value
- [ ] Debug mode is disabled
- [ ] HTTPS is configured
- [ ] File upload limits are set
- [ ] Disk space monitoring is active
- [ ] Log rotation is configured
- [ ] Backups are scheduled
- [ ] Health checks are in place
- [ ] Firewall rules are configured
- [ ] Dependencies are up to date