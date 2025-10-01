FROM python:3.11-slim

# Install system dependencies including FFmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create non-root user
RUN groupadd -r processor && useradd -r -g processor processor

# Create necessary directories
RUN mkdir -p /tmp/video_processing /var/log && \
    chown -R processor:processor /app /tmp/video_processing /var/log

# Switch to non-root user
USER processor

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.path.append('/app'); from main import VideoProcessorWorker; worker = VideoProcessorWorker(); import asyncio; result = asyncio.run(worker.health_check()); exit(0 if result['status'] == 'healthy' else 1)"

# Start the worker
CMD ["python", "main.py"]