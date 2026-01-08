# ============================================================================
# views.py - Flask Routes and Views
# ============================================================================
"""
Flask routes for PDF processing application.
"""
from flask import Blueprint, render_template, request, send_file, jsonify, current_app
from werkzeug.utils import secure_filename
import os
import uuid

from models import JobStatus
from .utils import (
    processing_status,
    processing_queues,
    start_processing_job,
    cleanup_job_files,
    get_job_status
)
import queue

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Main page"""
    return render_template('index.html')


@main_bp.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and start processing"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'Only PDF files are allowed'}), 400

    # Generate unique job ID
    job_id = str(uuid.uuid4())

    # Secure filename and create paths
    filename = secure_filename(file.filename)
    input_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f"{job_id}_{filename}")
    output_path = os.path.join(current_app.config['OUTPUT_FOLDER'], f"{job_id}_{filename}")
    tmp_path = os.path.join(current_app.config['TMP_FOLDER'], f"{job_id}_{filename}")

    # Save uploaded file
    file.save(input_path)

    # Initialize job tracking
    processing_status[job_id] = JobStatus(
        job_id=job_id,
        filename=filename,
        status='queued',
        input_file=input_path,
        output_file=None
    )
    processing_queues[job_id] = queue.Queue()

    # Start background processing
    start_processing_job(job_id, input_path, output_path, tmp_path)

    return jsonify({'job_id': job_id, 'filename': filename})


@main_bp.route('/status/<job_id>')
def status(job_id):
    """Get processing status and messages"""
    status_data = get_job_status(job_id)

    if status_data is None:
        return jsonify({'error': 'Job not found'}), 404

    return jsonify(status_data)


@main_bp.route('/download/<job_id>')
def download(job_id):
    """Download processed PDF"""
    if job_id not in processing_status:
        return jsonify({'error': 'Job not found'}), 404

    job = processing_status[job_id]

    if job.status != 'completed':
        return jsonify({'error': 'Processing not complete'}), 400

    output_file = job.output_file
    if not output_file or not os.path.exists(output_file):
        return jsonify({'error': 'Output file not found'}), 404

    return send_file(
        output_file,
        as_attachment=True,
        download_name=f"tagged_{job.filename}"
    )


@main_bp.route('/cleanup/<job_id>', methods=['POST'])
def cleanup(job_id):
    """Clean up job files"""
    if cleanup_job_files(job_id):
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Job not found'}), 404