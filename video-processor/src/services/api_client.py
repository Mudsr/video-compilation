import asyncio
import aiohttp
import json
import logging
from datetime import datetime
from typing import Optional
from src.models import VideoCompilationJob, CompilationResult

logger = logging.getLogger(__name__)

class APIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        
    async def update_video_status(
        self, 
        request_id: str, 
        status: str, 
        video_url: Optional[str] = None,
        error_message: Optional[str] = None,
        compilation_time: Optional[float] = None
    ) -> bool:
        """Update video compilation status in the API service"""
        try:
            url = f"{self.base_url}/api/video/{request_id}/status"
            data = {
                "status": status,
                "video_url": video_url,
                "error_message": error_message,
                "compilation_time": compilation_time,
                "completed_at": None if status != "completed" else datetime.now().isoformat()
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.patch(url, json=data) as response:
                    if response.status == 200:
                        logger.info(f"Updated status for {request_id} to {status}")
                        return True
                    else:
                        logger.error(f"Failed to update status for {request_id}: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Error updating status for {request_id}: {e}")
            return False
    
    async def get_frames_info(self, request_id: str) -> Optional[list]:
        """Get frame information from API service"""
        try:
            url = f"{self.base_url}/api/frames/{request_id}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('frames', [])
                    else:
                        logger.error(f"Failed to get frames for {request_id}: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error getting frames for {request_id}: {e}")
            return None