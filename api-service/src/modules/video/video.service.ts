import { Injectable, NotFoundException, BadRequestException } from '@nestjs/common';
import { PrismaService } from '../../common/services/prisma.service';
import { QueueService } from '../../common/services/queue.service';
import { StorageService } from '../../common/services/storage.service';

@Injectable()
export class VideoService {
  constructor(
    private prisma: PrismaService,
    private queueService: QueueService,
    private storageService: StorageService,
  ) {}

  async updateVideoStatus(
    requestId: string,
    updateData: {
      status: string;
      video_url?: string;
      error_message?: string;
      compilation_time?: number;
      completed_at?: string;
    }
  ) {
    try {
      const videoRequest = await this.prisma.videoRequest.findUnique({
        where: { requestId },
      });

      if (!videoRequest) {
        throw new NotFoundException(`Video request ${requestId} not found`);
      }

      const updatedRequest = await this.prisma.videoRequest.update({
        where: { requestId },
        data: {
          status: updateData.status,
          videoUrl: updateData.video_url,
          errorMessage: updateData.error_message,
          compilationTime: updateData.compilation_time,
          completedAt: updateData.completed_at ? new Date(updateData.completed_at) : null,
          updatedAt: new Date(),
        },
      });

      return {
        success: true,
        message: `Status updated for request ${requestId}`,
        status: updatedRequest.status,
      };
    } catch (error) {
      if (error instanceof NotFoundException) {
        throw error;
      }
      console.error(`Error updating status for ${requestId}:`, error);
      throw new BadRequestException('Failed to update video status');
    }
  }

  async getVideoStatus(requestId: string) {
    const videoRequest = await this.prisma.videoRequest.findUnique({
      where: { requestId },
      include: {
        frames: true,
      },
    });

    if (!videoRequest) {
      throw new NotFoundException(`Video request ${requestId} not found`);
    }

    let videoUrl = null;
    if (videoRequest.videoUrl && videoRequest.status === 'completed') {
      videoUrl = await this.storageService.getVideoUrl(videoRequest.videoUrl);
    }

    return {
      requestId: videoRequest.requestId,
      status: videoRequest.status,
      totalFrames: videoRequest.totalFrames,
      framesReceived: videoRequest.framesReceived,
      progress: {
        percentage: Math.round((videoRequest.framesReceived / videoRequest.totalFrames) * 100),
        isComplete: videoRequest.framesReceived >= videoRequest.totalFrames,
      },
      videoUrl,
      compilationTime: videoRequest.compilationTime,
      errorMessage: videoRequest.errorMessage,
      createdAt: videoRequest.createdAt,
      updatedAt: videoRequest.updatedAt,
      completedAt: videoRequest.completedAt,
    };
  }

  async getAllVideoRequests(
    page: number = 1,
    limit: number = 20,
    status?: string,
  ) {
    const skip = (page - 1) * limit;
    const where = status ? { status } : {};

    const [videoRequests, total] = await Promise.all([
      this.prisma.videoRequest.findMany({
        where,
        skip,
        take: limit,
        orderBy: { createdAt: 'desc' },
        include: {
          _count: {
            select: { frames: true },
          },
        },
      }),
      this.prisma.videoRequest.count({ where }),
    ]);

    return {
      data: videoRequests.map(request => ({
        requestId: request.requestId,
        status: request.status,
        totalFrames: request.totalFrames,
        framesReceived: request.framesReceived,
        progress: Math.round((request.framesReceived / request.totalFrames) * 100),
        compilationTime: request.compilationTime,
        createdAt: request.createdAt,
        completedAt: request.completedAt,
      })),
      pagination: {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit),
      },
    };
  }

  async retryVideoCompilation(requestId: string) {
    const videoRequest = await this.prisma.videoRequest.findUnique({
      where: { requestId },
    });

    if (!videoRequest) {
      throw new NotFoundException(`Video request ${requestId} not found`);
    }

    if (videoRequest.status === 'completed') {
      return {
        success: false,
        message: 'Video compilation already completed',
      };
    }

    if (videoRequest.framesReceived < videoRequest.totalFrames) {
      return {
        success: false,
        message: 'Cannot retry - not all frames have been uploaded yet',
      };
    }

    // Reset status and queue for retry
    await this.prisma.videoRequest.update({
      where: { requestId },
      data: {
        status: 'processing',
        errorMessage: null,
      },
    });

    await this.queueService.publishVideoCompilationJob({
      requestId: videoRequest.requestId,
      totalFrames: videoRequest.totalFrames,
      outputFormat: videoRequest.outputFormat,
      fps: videoRequest.fps,
      quality: videoRequest.quality,
    }, 8); // Higher priority for retries

    return {
      success: true,
      message: `Video compilation for ${requestId} queued for retry`,
    };
  }

  async getQueueStats() {
    return this.queueService.getQueueStats();
  }

  async getSystemHealth() {
    try {
      const queueStats = await this.queueService.getQueueStats();
      const storageStats = await this.storageService.getStorageStats();
      
      const [totalRequests, pendingRequests, processingRequests, completedRequests, failedRequests] = await Promise.all([
        this.prisma.videoRequest.count(),
        this.prisma.videoRequest.count({ where: { status: 'pending' } }),
        this.prisma.videoRequest.count({ where: { status: 'processing' } }),
        this.prisma.videoRequest.count({ where: { status: 'completed' } }),
        this.prisma.videoRequest.count({ where: { status: 'failed' } }),
      ]);

      return {
        status: 'healthy',
        timestamp: new Date().toISOString(),
        queue: {
          pendingJobs: queueStats.messageCount,
          activeWorkers: queueStats.consumerCount,
        },
        storage: storageStats,
        database: {
          totalRequests,
          pending: pendingRequests,
          processing: processingRequests,
          completed: completedRequests,
          failed: failedRequests,
        },
      };
    } catch (error: any) {
      return {
        status: 'unhealthy',
        timestamp: new Date().toISOString(),
        error: error.message,
      };
    }
  }
}