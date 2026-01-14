"""
Flask routes for PDF processing application.
"""
from flask import Blueprint, render_template, request, send_file, jsonify, current_app
from werkzeug.utils import secure_filename
import os
import uuid
import queue

from models import JobStatus
from utils import (
    processing_queues,
    start_processing_job,
    cleanup_job_files,
    get_job_status,
    save_job_status,
    load_job_status
)

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

    # Initialize job tracking - save to file
    job_status = JobStatus(
        job_id=job_id,
        filename=filename,
        status='queued',
        input_file=input_path,
        output_file=None
    )
    save_job_status(job_id, job_status)
    processing_queues[job_id] = queue.Queue()

    print(f"Job {job_id} initialized with status 'queued'")

    # Start background processing AFTER job is fully set up
    start_processing_job(job_id, input_path, output_path, tmp_path, filename)

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
    job = load_job_status(job_id)

    if not job:
        print(f"Download error: Job {job_id} not found")
        return jsonify({'error': 'Job not found'}), 404

    print(f"Download request for job {job_id}: status={job.status}, output_file={job.output_file}")

    if job.status != 'completed':
        print(f"Download error: Job status is {job.status}, not completed")
        return jsonify({'error': f'Processing not complete. Status: {job.status}'}), 400

    output_file = job.output_file
    if not output_file:
        print(f"Download error: No output file set for job {job_id}")
        return jsonify({'error': 'Output file not set'}), 404

    if not os.path.exists(output_file):
        print(f"Download error: Output file does not exist: {output_file}")
        return jsonify({'error': f'Output file not found: {output_file}'}), 404

    print(f"Sending file: {output_file}")
    return send_file(
        output_file,
        as_attachment=True,
        download_name=f"tagged_{job.filename}"
    )


@main_bp.route('/cleanup/<job_id>', methods=['POST'])
def cleanup(job_id):
    """Clean up job files"""
    print(f"Cleanup request for job {job_id}")
    if cleanup_job_files(job_id):
        print(f"Cleanup successful for job {job_id}")
        return jsonify({'success': True})
    else:
        print(f"Cleanup failed: Job {job_id} not found")
        return jsonify({'error': 'Job not found'}), 404