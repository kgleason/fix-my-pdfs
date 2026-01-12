# ============================================================================
# models.py - Data Classes and Models
# ============================================================================
"""
Data models for PDF processing application.
"""
from dataclasses import dataclass, asdict
from typing import Optional, List
from datetime import datetime


@dataclass
class PDFBlock:
    """Represents a structured block in the PDF"""
    type: str  # 'heading', 'paragraph', 'table', 'list_item'
    text: str
    size: Optional[float] = None
    data: Optional[list] = None


@dataclass
class ProcessingMessage:
    """Message for progress updates"""
    type: str  # 'info', 'warning', 'error', 'success', 'progress'
    message: str
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().strftime('%H:%M:%S')

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


@dataclass
class JobStatus:
    """Tracks the status of a PDF processing job"""
    job_id: str
    filename: str
    status: str  # 'queued', 'processing', 'completed', 'failed'
    input_file: str
    output_file: Optional[str] = None
    error: Optional[str] = None
    created_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return asdict(self)