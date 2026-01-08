# ============================================================================
# app.py - Application Entry Point
# ============================================================================
"""
Flask application entry point for PDF auto-tagging service.
Run this file to start the application.
"""
from flask import Flask
import os


def create_app():
    """Application factory pattern"""
    app = Flask(__name__)

    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['UPLOAD_FOLDER'] = 'uploads'
    app.config['OUTPUT_FOLDER'] = 'outputs'
    app.config['TMP_FOLDER'] = 'tmp'
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

    # Create necessary folders
    for folder in [app.config['UPLOAD_FOLDER'], app.config['OUTPUT_FOLDER'], app.config['TMP_FOLDER']]:
        os.makedirs(folder, exist_ok=True)

    # Register blueprints
    from views import main_bp
    app.register_blueprint(main_bp)

    return app

# Create app instance at module level for gunicorn
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, threaded=True)

