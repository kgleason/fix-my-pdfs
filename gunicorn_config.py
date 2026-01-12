# ============================================================================
# gunicorn_config.py - Gunicorn Configuration
# ============================================================================
"""
Gunicorn configuration file for PDF Tagger application.
"""
import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8880"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gthread"  # Use threaded workers for background processing
threads = 2  # Number of threads per worker
worker_connections = 1000
max_requests = 1000  # Restart workers after this many requests
max_requests_jitter = 100  # Add randomness to max_requests
timeout = 300  # 5 minutes - increased for large PDF processing
keepalive = 2

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "pdf_tagger"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (uncomment and configure for HTTPS)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"