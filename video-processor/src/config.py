import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # RabbitMQ
    rabbitmq_url: str = "amqp://admin:admin123@localhost:5672"
    queue_name: str = "video_compilation_queue"
    
    # MinIO Storage
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin123"
    minio_secure: bool = False
    frames_bucket: str = "video-frames"
    videos_bucket: str = "compiled-videos"
    
    # Video Processing
    max_concurrent_jobs: int = 4
    max_compilation_time: int = 300  # 5 minutes
    temp_dir: str = "/tmp/video_processing"
    
    # FFmpeg Settings
    ffmpeg_binary: str = "ffmpeg"
    default_fps: int = 30
    default_quality: str = "medium"
    
    # Worker Settings
    worker_id: str = os.getenv("HOSTNAME", "worker-1")
    prefetch_count: int = 1  # Process one job at a time per worker
    
    # Health Check
    health_check_interval: int = 30
    
    # API Service
    api_service_url: str = "http://api-service:3000"
    
    class Config:
        env_file = ".env"

settings = Settings()