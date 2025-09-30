import {
  Controller,
  Get,
  Post,
  Put,
  Patch,
  Param,
  Query,
  Body,
  ParseIntPipe,
} from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse, ApiParam, ApiQuery, ApiBody } from '@nestjs/swagger';
import { VideoService } from './video.service';

class UpdateStatusDto {
  status: string;
  video_url?: string;
  error_message?: string;
  compilation_time?: number;
  completed_at?: string;
}

@ApiTags('video')
@Controller('api/video')
export class VideoController {
  constructor(private readonly videoService: VideoService) {}

  @Get(':requestId/status')
  @ApiOperation({ summary: 'Get video compilation status' })
  @ApiParam({ name: 'requestId', description: 'Video request ID' })
  @ApiResponse({ status: 200, description: 'Status retrieved successfully' })
  @ApiResponse({ status: 404, description: 'Video request not found' })
  async getVideoStatus(@Param('requestId') requestId: string) {
    return this.videoService.getVideoStatus(requestId);
  }

  @Patch(':requestId/status')
  @ApiOperation({ summary: 'Update video compilation status (for video processor)' })
  @ApiParam({ name: 'requestId', description: 'Video request ID' })
  @ApiBody({ type: UpdateStatusDto })
  @ApiResponse({ status: 200, description: 'Status updated successfully' })
  @ApiResponse({ status: 404, description: 'Video request not found' })
  async updateVideoStatus(
    @Param('requestId') requestId: string,
    @Body() updateData: UpdateStatusDto,
  ) {
    return this.videoService.updateVideoStatus(requestId, updateData);
  }

  @Get('requests')
  @ApiOperation({ summary: 'Get all video requests with pagination' })
  @ApiQuery({ name: 'page', required: false, description: 'Page number (default: 1)' })
  @ApiQuery({ name: 'limit', required: false, description: 'Items per page (default: 20)' })
  @ApiQuery({ name: 'status', required: false, description: 'Filter by status' })
  @ApiResponse({ status: 200, description: 'Video requests retrieved successfully' })
  async getAllVideoRequests(
    @Query('page', new ParseIntPipe({ optional: true })) page: number = 1,
    @Query('limit', new ParseIntPipe({ optional: true })) limit: number = 20,
    @Query('status') status?: string,
  ) {
    return this.videoService.getAllVideoRequests(page, limit, status);
  }

  @Post(':requestId/retry')
  @ApiOperation({ summary: 'Retry failed video compilation' })
  @ApiParam({ name: 'requestId', description: 'Video request ID' })
  @ApiResponse({ status: 200, description: 'Retry initiated successfully' })
  @ApiResponse({ status: 404, description: 'Video request not found' })
  async retryVideoCompilation(@Param('requestId') requestId: string) {
    return this.videoService.retryVideoCompilation(requestId);
  }

  @Get('queue/stats')
  @ApiOperation({ summary: 'Get queue statistics' })
  @ApiResponse({ status: 200, description: 'Queue stats retrieved successfully' })
  async getQueueStats() {
    return this.videoService.getQueueStats();
  }

  @Get('health')
  @ApiOperation({ summary: 'Get system health status' })
  @ApiResponse({ status: 200, description: 'Health status retrieved successfully' })
  async getSystemHealth() {
    return this.videoService.getSystemHealth();
  }
}