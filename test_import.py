# ============================================================================
# test_import.py - Test Script to Verify Module Imports
# ============================================================================
#!/usr/bin/env python3
"""
Test script to verify all modules can be imported correctly.
Run this before building Docker container to catch import errors.
"""

print("Testing module imports...")

try:
    print("1. Importing models...")
    from models import PDFBlock, ProcessingMessage, JobStatus
    print("   ✓ models imported successfully")
except Exception as e:
    print(f"   ✗ Failed to import models: {e}")
    exit(1)

try:
    print("2. Importing pdf_tagger...")
    from pdf_tagger import PDFTagger
    print("   ✓ pdf_tagger imported successfully")
except Exception as e:
    print(f"   ✗ Failed to import pdf_tagger: {e}")
    exit(1)

try:
    print("3. Importing utils...")
    from utils import process_pdf_background, start_processing_job
    print("   ✓ utils imported successfully")
except Exception as e:
    print(f"   ✗ Failed to import utils: {e}")
    exit(1)

try:
    print("4. Importing views...")
    from views import main_bp
    print("   ✓ views imported successfully")
except Exception as e:
    print(f"   ✗ Failed to import views: {e}")
    exit(1)

try:
    print("5. Importing app...")
    from app import app, create_app
    print("   ✓ app imported successfully")
    print(f"   ✓ app object type: {type(app)}")
    print(f"   ✓ app name: {app.name}")
except Exception as e:
    print(f"   ✗ Failed to import app: {e}")
    exit(1)

print("\n✓ All imports successful!")
print("\nYou can now run:")
print("  - Development: python app.py")
print("  - Production:  gunicorn --config gunicorn_config.py app:app")
print("  - Docker:      docker build -t pdf-tagger . && docker run -p 8000:8000 pdf-tagger")
