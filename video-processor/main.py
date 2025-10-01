import asyncio
import logging
import os
import sys
import time
import psutil
from typing import Optional
from datetime import datetime

# Add src to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config import settings
from src.models import VideoCompilationJob, CompilationResult, WorkerStats
from src.services.queue_consumer import QueueConsumer, setup_signal_handlers
from src.services.video_compiler import VideoCompiler
from src.services.storage_service import StorageService
from src.services.api_client import APIClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/var/log/video-processor.log') if os.path.exists('/var/log') else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)

class VideoProcessorWorker:
    def __init__(self):
        self.worker_id = settings.worker_id
        self.start_time = time.time()
        self.stats = WorkerStats(
            worker_id=self.worker_id,
            active_jobs=0,
            completed_jobs=0,
            failed_jobs=0,
            uptime=0,
            cpu_usage=0,
            memory_usage=0
        )
        
        # Initialize services
        self.queue_consumer = QueueConsumer(
            rabbitmq_url=settings.rabbitmq_url,
            queue_name=settings.queue_name,
            prefetch_count=settings.prefetch_count
        )
        
        self.video_compiler = VideoCompiler(
            ffmpeg_binary=settings.ffmpeg_binary,
            temp_dir=settings.temp_dir
        )
        
        self.storage_service = StorageService(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
            frames_bucket=settings.frames_bucket,
            videos_bucket=settings.videos_bucket
        )
        
        self.api_client = APIClient(settings.api_service_url)
        
        # Set job handler
        self.queue_consumer.set_job_handler(self.process_video_compilation_job)
        
        logger.info(f"Video Processor Worker {self.worker_id} initialized")
    
    async def process_video_compilation_job(self, job: VideoCompilationJob) -> bool:
        """Process a video compilation job"""
        request_id = job.request_id
        
        try:
            self.stats.active_jobs += 1
            logger.info(f"🎬 Processing video compilation for {request_id}")
            
            # Update status to processing
            await self.api_client.update_video_status(request_id, "processing")
            
            # Download frames from storage
            frames = await self.storage_service.download_all_frames(
                request_id,
                job.total_frames,
                settings.temp_dir
            )
            
            if len(frames) != job.total_frames:
                error_msg = f"Downloaded {len(frames)}/{job.total_frames} frames"
                logger.error(f"{error_msg}")
                await self.api_client.update_video_status(
                    request_id, 
                    "failed", 
                    error_message=error_msg
                )
                self.stats.failed_jobs += 1
                return False
            
            # Compile video
            result = await self.video_compiler.compile_video(
                request_id=request_id,
                frames=frames,
                fps=job.fps,
                quality=job.quality,
                output_format=job.output_format,
                max_compilation_time=settings.max_compilation_time
            )
            
            if result.success and result.video_url:
                # Upload video to storage
                video_filename = await self.storage_service.upload_video(
                    request_id,
                    result.video_url
                )
                
                if video_filename:
                    # Update status to completed
                    await self.api_client.update_video_status(
                        request_id,
                        "completed",
                        video_url=video_filename,
                        compilation_time=result.compilation_time
                    )
                    self.stats.completed_jobs += 1
                    
                    logger.info(f"Video compilation completed for {request_id}")
                    return True
                else:
                    # Upload failed
                    await self.api_client.update_video_status(
                        request_id,
                        "failed",
                        error_message="Failed to upload compiled video",
                        compilation_time=result.compilation_time
                    )
                    self.stats.failed_jobs += 1
                    return False
            else:
                # Compilation failed
                await self.api_client.update_video_status(
                    request_id,
                    "failed",
                    error_message=result.error_message,
                    compilation_time=result.compilation_time
                )
                self.stats.failed_jobs += 1
                return False
                
        except Exception as e:
            logger.error(f"Unexpected error processing {request_id}: {e}")
            await self.api_client.update_video_status(
                request_id,
                "failed",
                error_message=f"Worker error: {str(e)}"
            )
            self.stats.failed_jobs += 1
            return False
            
        finally:
            self.stats.active_jobs -= 1
            
            # Cleanup
            try:
                await self.video_compiler.cleanup_work_directory(request_id)
                await self.storage_service.cleanup_frames(
                    request_id,
                    os.path.join(settings.temp_dir, request_id, "frames")
                )
            except Exception as e:
                logger.error(f"Error during cleanup for {request_id}: {e}")
    
    async def health_check(self) -> dict:
        """Perform health check on all services"""
        self.update_stats()
        
        health_status = {
            "worker_id": self.worker_id,
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "uptime": self.stats.uptime,
            "stats": {
                "active_jobs": self.stats.active_jobs,
                "completed_jobs": self.stats.completed_jobs,
                "failed_jobs": self.stats.failed_jobs,
                "cpu_usage": self.stats.cpu_usage,
                "memory_usage": self.stats.memory_usage
            },
            "services": {
                "queue": self.queue_consumer.health_check(),
                "ffmpeg": self.video_compiler.health_check(),
                "storage": self.storage_service.health_check()
            }
        }
        
        # Check if any service is unhealthy
        if not all(health_status["services"].values()):
            health_status["status"] = "unhealthy"
        
        return health_status
    
    def update_stats(self):
        """Update worker statistics"""
        self.stats.uptime = time.time() - self.start_time
        self.stats.cpu_usage = psutil.cpu_percent()
        self.stats.memory_usage = psutil.virtual_memory().percent
    
    def start(self):
        """Start the worker"""
        logger.info(f"Starting Video Processor Worker {self.worker_id}")
        
        # Setup signal handlers for graceful shutdown
        setup_signal_handlers(self.queue_consumer)
        
        # Create temp directory if it doesn't exist
        os.makedirs(settings.temp_dir, exist_ok=True)
        
        # Start consuming jobs
        self.queue_consumer.start_consuming()

def main():
    """Main entry point"""
    try:
        worker = VideoProcessorWorker()
        worker.start()
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Worker failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()