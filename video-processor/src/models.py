from dataclasses import dataclass
from typing import Optional
from datetime import datetime
from enum import Enum

class VideoStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class VideoQuality(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"

@dataclass
class VideoCompilationJob:
    request_id: str
    total_frames: int
    output_format: str = "mp4"
    fps: int = 30
    quality: str = "medium"

@dataclass
class FrameInfo:
    frame_number: int
    frame_url: str
    local_path: Optional[str] = None

@dataclass
class CompilationResult:
    request_id: str
    success: bool
    video_url: Optional[str] = None
    error_message: Optional[str] = None
    compilation_time: Optional[float] = None
    completed_at: Optional[datetime] = None
    
@dataclass
class WorkerStats:
    worker_id: str
    active_jobs: int
    completed_jobs: int
    failed_jobs: int
    uptime: float
    cpu_usage: float
    memory_usage: float