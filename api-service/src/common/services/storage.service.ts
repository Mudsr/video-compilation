import { Injectable, OnModuleInit } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import * as Minio from 'minio';

@Injectable()
export class StorageService implements OnModuleInit {
  private minioClient: Minio.Client;
  private readonly framesBucket = 'video-frames';
  private readonly videosBucket = 'compiled-videos';

  constructor(private configService: ConfigService) {}

  async onModuleInit() {
    const endpoint = this.configService.get<string>('MINIO_ENDPOINT') || 'localhost:9000';
    const accessKey = this.configService.get<string>('MINIO_ACCESS_KEY') || 'minioadmin';
    const secretKey = this.configService.get<string>('MINIO_SECRET_KEY') || 'minioadmin123';
    const useSSLString = this.configService.get<string>('MINIO_USE_SSL') || 'false';
    const useSSL = useSSLString.toLowerCase() === 'true';

    this.minioClient = new Minio.Client({
      endPoint: endpoint.split(':')[0],
      port: parseInt(endpoint.split(':')[1]) || 9000,
      useSSL,
      accessKey,
      secretKey,
    });

    // Create buckets if they don't exist
    await this.ensureBucketExists(this.framesBucket);
    await this.ensureBucketExists(this.videosBucket);

    console.log('MinIO storage connected successfully');
  }

  private async ensureBucketExists(bucketName: string): Promise<void> {
    try {
      const exists = await this.minioClient.bucketExists(bucketName);
      if (!exists) {
        await this.minioClient.makeBucket(bucketName);
        console.log(`Created bucket: ${bucketName}`);
      }
    } catch (error) {
      console.error(`Error ensuring bucket ${bucketName}:`, error);
      throw error;
    }
  }

  async uploadFrame(
    requestId: string,
    frameNumber: number,
    buffer: Buffer,
    originalName: string,
  ): Promise<string> {
    const extension = originalName.split('.').pop()?.toLowerCase() || 'jpg';
    const fileName = `${requestId}/frame_${frameNumber.toString().padStart(6, '0')}.${extension}`;

    try {
      await this.minioClient.putObject(this.framesBucket, fileName, buffer, buffer.length, {
        'Content-Type': `image/${extension}`,
        'X-Request-ID': requestId,
        'X-Frame-Number': frameNumber.toString(),
      });

      return fileName;
    } catch (error) {
      console.error(`Error uploading frame ${frameNumber} for request ${requestId}:`, error);
      throw error;
    }
  }

  async getFrameUrl(fileName: string): Promise<string> {
    try {
      // Generate a presigned URL valid for 1 hour
      return await this.minioClient.presignedGetObject(this.framesBucket, fileName, 3600);
    } catch (error) {
      console.error(`Error generating frame URL for ${fileName}:`, error);
      throw error;
    }
  }

  async uploadVideo(requestId: string, buffer: Buffer): Promise<string> {
    const fileName = `${requestId}/compiled_video.mp4`;

    try {
      await this.minioClient.putObject(this.videosBucket, fileName, buffer, buffer.length, {
        'Content-Type': 'video/mp4',
        'X-Request-ID': requestId,
      });

      return fileName;
    } catch (error) {
      console.error(`Error uploading compiled video for request ${requestId}:`, error);
      throw error;
    }
  }

  async getVideoUrl(fileName: string): Promise<string> {
    try {
      // Generate a presigned URL valid for 24 hours
      return await this.minioClient.presignedGetObject(this.videosBucket, fileName, 86400);
    } catch (error) {
      console.error(`Error generating video URL for ${fileName}:`, error);
      throw error;
    }
  }

  async deleteFrames(requestId: string): Promise<void> {
    try {
      const objectsStream = this.minioClient.listObjects(this.framesBucket, `${requestId}/`);
      const objectsList: string[] = [];

      objectsStream.on('data', (obj) => {
        if (obj.name) objectsList.push(obj.name);
      });

      objectsStream.on('end', async () => {
        if (objectsList.length > 0) {
          await this.minioClient.removeObjects(this.framesBucket, objectsList);
          console.log(`🗑️ Deleted ${objectsList.length} frames for request ${requestId}`);
        }
      });
    } catch (error) {
      console.error(`Error deleting frames for request ${requestId}:`, error);
    }
  }

  async getStorageStats(): Promise<{ framesBucketSize: number; videosBucketSize: number }> {
    try {
      return {
        framesBucketSize: 0, 
        videosBucketSize: 0,
      };
    } catch (error) {
      console.error('Error getting storage stats:', error);
      return { framesBucketSize: 0, videosBucketSize: 0 };
    }
  }
}