import os
import asyncio
import subprocess
import time
import logging
from typing import List, Optional, Dict
from src.models import FrameInfo, CompilationResult, VideoQuality

logger = logging.getLogger(__name__)

class VideoCompiler:
    def __init__(self, ffmpeg_binary: str = "ffmpeg", temp_dir: str = "/tmp/video_processing"):
        self.ffmpeg_binary = ffmpeg_binary
        self.temp_dir = temp_dir
        
        # Quality presets for different video qualities
        self.quality_presets = {
            VideoQuality.LOW: {
                "crf": 28,
                "preset": "fast",
                "scale": "720:480"
            },
            VideoQuality.MEDIUM: {
                "crf": 23,
                "preset": "medium", 
                "scale": "1280:720"
            },
            VideoQuality.HIGH: {
                "crf": 18,
                "preset": "slow",
                "scale": "1920:1080"
            },
            VideoQuality.ULTRA: {
                "crf": 15,
                "preset": "veryslow",
                "scale": "1920:1080"
            }
        }
    
    async def compile_video(
        self,
        request_id: str,
        frames: List[FrameInfo],
        fps: int = 30,
        quality: str = "medium",
        output_format: str = "mp4",
        max_compilation_time: int = 300
    ) -> CompilationResult:
        """Compile frames into a video using FFmpeg"""
        start_time = time.time()
        
        try:
            if not frames:
                return CompilationResult(
                    request_id=request_id,
                    success=False,
                    error_message="No frames provided for compilation"
                )
            
            # Sort frames by frame number
            sorted_frames = sorted(frames, key=lambda x: x.frame_number)
            
            # Prepare temporary directories
            work_dir = os.path.join(self.temp_dir, request_id)
            frames_dir = os.path.join(work_dir, "frames")
            output_path = os.path.join(work_dir, f"output.{output_format}")
            
            os.makedirs(work_dir, exist_ok=True)
            
            # Create frame list file for FFmpeg
            frame_list_path = os.path.join(work_dir, "frame_list.txt")
            await self._create_frame_list_file(sorted_frames, frame_list_path, fps)
            
            # Get quality settings
            quality_settings = self.quality_presets.get(quality, self.quality_presets[VideoQuality.MEDIUM])
            
            # Build FFmpeg command
            cmd = await self._build_ffmpeg_command(
                frame_list_path,
                output_path,
                fps,
                quality_settings,
                output_format
            )
            
            logger.info(f"🎬 Starting video compilation for {request_id} with {len(sorted_frames)} frames")
            
            # Run FFmpeg with timeout
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=work_dir
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=max_compilation_time
                )
                
                compilation_time = time.time() - start_time
                
                if process.returncode == 0:
                    # Check if output file exists and has reasonable size
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 1024:  # At least 1KB
                        logger.info(f"Video compilation completed for {request_id} in {compilation_time:.2f}s")
                        
                        return CompilationResult(
                            request_id=request_id,
                            success=True,
                            video_url=output_path,  # Will be updated after upload
                            compilation_time=compilation_time
                        )
                    else:
                        return CompilationResult(
                            request_id=request_id,
                            success=False,
                            error_message="FFmpeg completed but output file is invalid or too small",
                            compilation_time=compilation_time
                        )
                else:
                    error_msg = stderr.decode('utf-8') if stderr else "Unknown FFmpeg error"
                    logger.error(f"FFmpeg failed for {request_id}: {error_msg}")
                    
                    return CompilationResult(
                        request_id=request_id,
                        success=False,
                        error_message=f"FFmpeg failed with code {process.returncode}: {error_msg}",
                        compilation_time=compilation_time
                    )
                    
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                
                return CompilationResult(
                    request_id=request_id,
                    success=False,
                    error_message=f"Video compilation timed out after {max_compilation_time} seconds"
                )
                
        except Exception as e:
            compilation_time = time.time() - start_time
            logger.error(f"Unexpected error during video compilation for {request_id}: {e}")
            
            return CompilationResult(
                request_id=request_id,
                success=False,
                error_message=f"Compilation error: {str(e)}",
                compilation_time=compilation_time
            )
    
    async def _create_frame_list_file(self, frames: List[FrameInfo], list_path: str, fps: int) -> None:
        """Create a frame list file for FFmpeg concat demuxer"""
        frame_duration = 1.0 / fps
        
        with open(list_path, 'w') as f:
            f.write("ffconcat version 1.0\n")
            for frame in frames:
                if frame.local_path and os.path.exists(frame.local_path):
                    f.write(f"file '{frame.local_path}'\n")
                    f.write(f"duration {frame_duration}\n")
            
            # Add the last frame again for proper duration
            if frames and frames[-1].local_path:
                f.write(f"file '{frames[-1].local_path}'\n")
    
    async def _build_ffmpeg_command(
        self,
        input_path: str,
        output_path: str,
        fps: int,
        quality_settings: Dict,
        output_format: str
    ) -> List[str]:
        """Build FFmpeg command with optimized settings"""
        
        cmd = [
            self.ffmpeg_binary,
            "-f", "concat",
            "-safe", "0",
            "-i", input_path,
            "-c:v", "libx264",
            "-preset", quality_settings["preset"],
            "-crf", str(quality_settings["crf"]),
            "-pix_fmt", "yuv420p",
            "-r", str(fps),
            "-movflags", "+faststart",  # Enable fast start for web streaming
            "-y",  # Overwrite output file
            output_path
        ]
        
        # Add scaling if specified
        if "scale" in quality_settings:
            cmd.extend(["-vf", f"scale={quality_settings['scale']}"])
        
        return cmd
    
    async def cleanup_work_directory(self, request_id: str) -> None:
        """Clean up temporary work directory"""
        try:
            import shutil
            work_dir = os.path.join(self.temp_dir, request_id)
            if os.path.exists(work_dir):
                shutil.rmtree(work_dir)
                logger.debug(f"🗑️ Cleaned up work directory for {request_id}")
        except Exception as e:
            logger.error(f"Error cleaning up work directory for {request_id}: {e}")
    
    def health_check(self) -> bool:
        """Check if FFmpeg is available and working"""
        try:
            result = subprocess.run(
                [self.ffmpeg_binary, "-version"],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"FFmpeg health check failed: {e}")
            return False