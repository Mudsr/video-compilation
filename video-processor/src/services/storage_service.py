import os
import asyncio
import aiofiles
import logging
from minio import Minio
from minio.error import S3Error
from typing import List, Optional
from src.models import FrameInfo

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        secure: bool = False,
        frames_bucket: str = "video-frames",
        videos_bucket: str = "compiled-videos"
    ):
        # Extract endpoint and port
        if ':' in endpoint:
            host, port = endpoint.split(':')
            port = int(port)
        else:
            host = endpoint
            port = 443 if secure else 80
            
        self.client = Minio(
            endpoint=f"{host}:{port}",
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
        self.frames_bucket = frames_bucket
        self.videos_bucket = videos_bucket
        
    async def download_frame(self, request_id: str, frame_number: int, local_path: str) -> bool:
        """Download a frame from storage to local filesystem"""
        try:
            # Construct the frame filename
            frame_filename = f"{request_id}/frame_{frame_number:06d}.jpg"
            
            # Download the frame
            response = self.client.get_object(self.frames_bucket, frame_filename)
            
            # Ensure local directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Write frame data to local file
            async with aiofiles.open(local_path, 'wb') as f:
                for data in response.stream(32*1024):
                    await f.write(data)
            
            response.close()
            response.release_conn()
            
            logger.debug(f"Downloaded frame {frame_number} for {request_id}")
            return True
            
        except S3Error as e:
            logger.error(f"S3 error downloading frame {frame_number} for {request_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error downloading frame {frame_number} for {request_id}: {e}")
            return False
    
    async def download_all_frames(self, request_id: str, total_frames: int, temp_dir: str) -> List[FrameInfo]:
        """Download all frames for a video request"""
        frames = []
        local_frame_dir = os.path.join(temp_dir, request_id, "frames")
        
        # Create semaphore to limit concurrent downloads
        semaphore = asyncio.Semaphore(10)  # Max 10 concurrent downloads
        
        async def download_single_frame(frame_num: int) -> Optional[FrameInfo]:
            async with semaphore:
                local_path = os.path.join(local_frame_dir, f"frame_{frame_num:06d}.jpg")
                
                if await self.download_frame(request_id, frame_num, local_path):
                    return FrameInfo(
                        frame_number=frame_num,
                        frame_url=f"{request_id}/frame_{frame_num:06d}.jpg",
                        local_path=local_path
                    )
                return None
        
        # Download all frames concurrently
        tasks = [download_single_frame(i) for i in range(1, total_frames + 1)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful downloads
        for result in results:
            if isinstance(result, FrameInfo):
                frames.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Frame download failed: {result}")
        
        logger.info(f"Downloaded {len(frames)}/{total_frames} frames for {request_id}")
        return sorted(frames, key=lambda x: x.frame_number)
    
    async def upload_video(self, request_id: str, video_path: str) -> Optional[str]:
        """Upload compiled video to storage"""
        try:
            video_filename = f"{request_id}/compiled_video.mp4"
            
            # Upload the video file
            self.client.fput_object(
                self.videos_bucket,
                video_filename,
                video_path,
                content_type="video/mp4",
                metadata={
                    "X-Request-ID": request_id,
                    "X-Content-Type": "compiled-video"
                }
            )
            
            logger.info(f"Uploaded compiled video for {request_id}")
            return video_filename
            
        except S3Error as e:
            logger.error(f"S3 error uploading video for {request_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error uploading video for {request_id}: {e}")
            return None
    
    async def cleanup_frames(self, request_id: str, local_frame_dir: str) -> None:
        """Clean up downloaded frames from local storage"""
        try:
            import shutil
            if os.path.exists(local_frame_dir):
                shutil.rmtree(local_frame_dir)
                logger.debug(f"🗑️ Cleaned up local frames for {request_id}")
        except Exception as e:
            logger.error(f"Error cleaning up frames for {request_id}: {e}")
    
    def health_check(self) -> bool:
        """Check if storage service is healthy"""
        try:
            # Try to list objects in frames bucket
            objects = self.client.list_objects(self.frames_bucket, max_keys=1)
            list(objects)  # Force evaluation
            return True
        except Exception as e:
            logger.error(f"Storage health check failed: {e}")
            return False