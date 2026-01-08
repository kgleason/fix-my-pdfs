# ============================================================================
# utils.py - Utility Functions and Helpers
# ============================================================================
"""
Utility functions for PDF processing application.
"""
import os
import threading
import queue
from typing import Dict

from models import JobStatus, ProcessingMessage
from pdf_tagger import PDFTagger

# Global state management
processing_status: Dict[str, JobStatus] = {}
processing_queues: Dict[str, queue.Queue] = {}


def process_pdf_background(job_id: str, input_path: str, output_path: str, tmp_path: str, original_filename: str):
    """Background processing function for PDF tagging"""
    try:
        # Update status
        if job_id in processing_status:
            status = processing_status[job_id]
            status.status = 'processing'

        # Create tagger and set message queue
        tagger = PDFTagger(input_path, output_path, tmp_path, job_id, original_filename)

        if job_id in processing_queues:
            tagger.set_message_queue(processing_queues[job_id])

        # Process the PDF
        success = tagger.process()

        # Update final status
        if job_id in processing_status:
            if success:
                processing_status[job_id].status = 'completed'
                processing_status[job_id].output_file = output_path
            else:
                processing_status[job_id].status = 'failed'

    except Exception as e:
        if job_id in processing_status:
            processing_status[job_id].status = 'failed'
            processing_status[job_id].error = str(e)

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
    if job_id not in processing_status:
        return False

    status = processing_status[job_id]

    # Delete input and output files
    for filepath in [status.input_file, status.output_file]:
        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception as e:
                print(f"Error removing file {filepath}: {e}")

    # Delete temp file
    tmp_filename = os.path.basename(status.input_file)
    tmp_path = os.path.join('tmp', tmp_filename)
    if os.path.exists(tmp_path):
        try:
            os.remove(tmp_path)
        except Exception as e:
            print(f"Error removing temp file {tmp_path}: {e}")

    # Remove from tracking
    del processing_status[job_id]
    if job_id in processing_queues:
        del processing_queues[job_id]

    return True


def get_job_status(job_id: str) -> dict:
    """Get the current status of a job"""
    if job_id not in processing_status:
        return None

    status = processing_status[job_id]

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
        'error': status.error
    }


