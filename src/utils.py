# ============================================================================
# utils.py - Utility Functions and Helpers
# ============================================================================
"""
Utility functions for PDF processing application.
"""
import os
import threading
import queue
import json
from typing import Dict
from pathlib import Path

from models import JobStatus, ProcessingMessage
from pdf_tagger import PDFTagger

# Job tracking directory
JOB_TRACKING_DIR = 'job_tracking'
os.makedirs(JOB_TRACKING_DIR, exist_ok=True)

# In-memory cache (per worker)
processing_queues: Dict[str, queue.Queue] = {}


def _get_job_file_path(job_id: str) -> str:
    """Get the file path for a job's status"""
    return os.path.join(JOB_TRACKING_DIR, f"{job_id}.json")


def save_job_status(job_id: str, status: JobStatus):
    """Save job status to file"""
    job_file = _get_job_file_path(job_id)
    with open(job_file, 'w') as f:
        json.dump(status.to_dict(), f)


def load_job_status(job_id: str) -> JobStatus:
    """Load job status from file"""
    job_file = _get_job_file_path(job_id)
    if not os.path.exists(job_file):
        return None

    try:
        with open(job_file, 'r') as f:
            data = json.load(f)
            return JobStatus(**data)
    except Exception as e:
        print(f"Error loading job status for {job_id}: {e}")
        return None


def delete_job_status(job_id: str):
    """Delete job status file"""
    job_file = _get_job_file_path(job_id)
    if os.path.exists(job_file):
        try:
            os.remove(job_file)
        except Exception as e:
            print(f"Error deleting job status for {job_id}: {e}")


def process_pdf_background(job_id: str, input_path: str, output_path: str, tmp_path: str, original_filename: str):
    """Background processing function for PDF tagging"""
    try:
        print(f"[{job_id}] Starting background processing")
        print(f"[{job_id}] Input: {input_path}")
        print(f"[{job_id}] Output: {output_path}")
        print(f"[{job_id}] Tmp: {tmp_path}")

        # Update status to processing
        status = load_job_status(job_id)
        if status:
            status.status = 'processing'
            save_job_status(job_id, status)
            print(f"[{job_id}] Status set to 'processing'")

        # Create tagger and set message queue
        tagger = PDFTagger(input_path, output_path, tmp_path, job_id, original_filename)

        if job_id in processing_queues:
            tagger.set_message_queue(processing_queues[job_id])

        # Process the PDF
        print(f"[{job_id}] Calling tagger.process()")
        success = tagger.process()
        print(f"[{job_id}] tagger.process() returned: {success}")

        # Update final status
        status = load_job_status(job_id)
        if status:
            if success:
                status.status = 'completed'
                status.output_file = output_path
                save_job_status(job_id, status)
                print(f"[{job_id}] Status set to 'completed', output_file: {output_path}")
                print(f"[{job_id}] Output file exists: {os.path.exists(output_path)}")
            else:
                status.status = 'failed'
                save_job_status(job_id, status)
                print(f"[{job_id}] Status set to 'failed'")

    except Exception as e:
        print(f"[{job_id}] Exception in background processing: {str(e)}")
        import traceback
        traceback.print_exc()

        status = load_job_status(job_id)
        if status:
            status.status = 'failed'
            status.error = str(e)
            save_job_status(job_id, status)

        # Send error message to queue
        msg = ProcessingMessage(type='error', message=f"Fatal error: {str(e)}")
        if job_id in processing_queues:
            processing_queues[job_id].put(msg.to_dict())


def start_processing_job(job_id: str, input_path: str, output_path: str, tmp_path: str, original_filename: str):
    """Start a background processing job"""
    thread = threading.Thread(
        target=process_pdf_background,
        args=(job_id, input_path, output_path, tmp_path, original_filename)
    )
    thread.daemon = True
    thread.start()


def cleanup_job_files(job_id: str) -> bool:
    """Clean up all files associated with a job"""
    status = load_job_status(job_id)
    if not status:
        return False

    # Delete input and output files
    for filepath in [status.input_file, status.output_file]:
        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception as e:
                print(f"Error removing file {filepath}: {e}")

    # Delete temp file
    tmp_filename = os.path.basename(status.input_file)
    tmp_path = os.path.join('../tmp', tmp_filename)
    if os.path.exists(tmp_path):
        try:
            os.remove(tmp_path)
        except Exception as e:
            print(f"Error removing temp file {tmp_path}: {e}")

    # Remove job status file
    delete_job_status(job_id)

    # Remove from queue tracking
    if job_id in processing_queues:
        del processing_queues[job_id]

    return True


def get_job_status(job_id: str) -> dict:
    """Get the current status of a job"""
    status = load_job_status(job_id)
    if not status:
        return None

    # Collect any queued messages
    messages = []
    if job_id in processing_queues:
        while not processing_queues[job_id].empty():
            try:
                messages.append(processing_queues[job_id].get_nowait())
            except queue.Empty:
                break

    return {
        'status': status.status,
        'filename': status.filename,
        'messages': messages,
        'error': status.error,
        'output_file': status.output_file
    }
