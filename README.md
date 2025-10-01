# Video Compilation System - Interview Assessment

## Overview

This is a distributed video compilation system designed to solve bottleneck issues in video processing. The system allows frames for a single request to be collected and compiled without being tied to a single server.

## Architecture

### Components

1. **API Service (NestJS)** - Handles frame uploads and provides REST endpoints
2. **Video Processor (Python)** - Consumes queue messages and compiles videos using FFmpeg
3. **RabbitMQ** - Message queue for job distribution
4. **MinIO** - S3-compatible object storage for frames and videos
5. **PostgreSQL/SQLite** - Database for metadata and request tracking

### Key Features

- **Distributed Processing**: Multiple video processor workers can run independently
- **Fault Tolerance**: If one worker fails, others continue processing
- **Horizontal Scaling**: Easy to add more workers for increased capacity
- **Resource Optimization**: FFmpeg processes are isolated and resource-controlled
- **Queue Management**: Priority-based job queue with retry mechanisms

## Technology Stack

- **Backend API**: NestJS 11.x with TypeScript
- **Video Processing**: Python 3.11 with FastAPI
- **Message Queue**: RabbitMQ 3.x
- **Object Storage**: MinIO (S3-compatible)
- **Database**: Prisma ORM with SQLite/PostgreSQL
- **Containerization**: Docker & Docker Compose
- **Video Processing**: FFmpeg

## Project Structure

```
video-compilation/
├── api-service/          # NestJS API service
│   ├── src/
│   │   ├── modules/      # Feature modules
│   │   ├── services/     # Shared services
│   │   └── common/       # Common utilities
│   ├── prisma/          # Database schema and migrations
│   └── Dockerfile
├── video-processor/      # Python video processing service
│   ├── src/
│   │   ├── services/     # Core services
│   │   └── utils/        # Utilities
│   ├── main.py          # Worker entry point
│   └── Dockerfile
├── shared/              # Shared configuration
└── docker-compose.yml   # Development environment
```

## Development Setup

1. **Prerequisites**
   - Docker & Docker Compose
   - Node.js 18+ (for API development)
   - Python 3.11+ (for video processor development)

2. **Start Development Environment**
   ```bash
   cd video-compilation
   docker-compose up -d
   ```

3. **API Service Development**
   ```bash
   cd api-service
   npm install
   npm run start:dev
   ```

4. **Video Processor Development**
   ```bash
   cd video-processor
   pip install -r requirements.txt
   python main.py
   ```

## API Endpoints

### Frame Upload
- `POST /api/frames/upload` - Upload individual frame
- `GET /api/frames/{requestId}` - Get frame upload status
- `DELETE /api/frames/{requestId}` - Delete request and frames

### Video Management
- `GET /api/video/{requestId}/status` - Get compilation status
- `GET /api/video/requests` - List all video requests
- `POST /api/video/{requestId}/retry` - Retry failed compilation

### Health & Monitoring
- `GET /api/video/health` - System health check
- `GET /api/video/queue/stats` - Queue statistics

## Performance Targets

- **Compilation Latency**: <5 seconds under normal load
- **Concurrent Compilations**: ≥500 concurrent without queue backlogs
- **Resource Usage**: ≤50% CPU per server during peak load
- **Fault Tolerance**: No single point of failure

## Scaling Strategy

1. **Horizontal Worker Scaling**: Add more video processor containers
2. **API Service Scaling**: Multiple API service instances behind load balancer
3. **Queue Sharding**: Multiple queue instances for different priorities
4. **Storage Optimization**: CDN integration for video delivery

**Note:** For true auto scaling we can opt to use kubernetes or ECS .

## Monitoring & Health Checks

- Worker health endpoints
- Queue depth monitoring
- Resource usage tracking
- Compilation time metrics
- Error rate monitoring

## Security Considerations

- Input validation for frame uploads
- File type restrictions
- Resource limits per request
- Rate limiting on API endpoints
- Secure storage with presigned URLs

This system addresses the original bottlenecks by:
- ✅ Distributing frames across multiple servers via object storage
- ✅ Enabling multiple concurrent video compilations
- ✅ Providing fault tolerance through multiple workers
- ✅ Optimizing resource usage with containerized workers
- ✅ Ensuring scalability for traffic spikes