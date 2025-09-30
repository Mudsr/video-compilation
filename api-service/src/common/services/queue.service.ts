import { Injectable, OnModuleInit, OnModuleDestroy } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import * as amqp from 'amqplib';

export interface VideoCompilationJob {
  requestId: string;
  totalFrames: number;
  outputFormat: string;
  fps: number;
  quality: string;
}

@Injectable()
export class QueueService implements OnModuleInit, OnModuleDestroy {
  private connection: any = null;
  private channel: any = null;
  private readonly queueName = 'video_compilation_queue';

  constructor(private configService: ConfigService) {}

  async onModuleInit() {
    try {
      const rabbitmqUrl = this.configService.get<string>('RABBITMQ_URL') || 'amqp://localhost:5672';
      this.connection = await amqp.connect(rabbitmqUrl);
      
      if (this.connection) {
        this.channel = await this.connection.createChannel();
        
        if (this.channel) {
          // Ensure queue exists with durability
          await this.channel.assertQueue(this.queueName, {
            durable: true,
            arguments: {
              'x-max-priority': 10, // Priority queue for urgent requests
            },
          });
        }
      }

      console.log('RabbitMQ connected successfully');
    } catch (error) {
      console.error('Failed to connect to RabbitMQ:', error);
      throw error;
    }
  }

  async onModuleDestroy() {
    try {
      if (this.channel) {
        await this.channel.close();
      }
      if (this.connection) {
        await this.connection.close();
      }
      console.log('RabbitMQ disconnected');
    } catch (error) {
      console.error('Error closing RabbitMQ connection:', error);
    }
  }

  async publishVideoCompilationJob(job: VideoCompilationJob, priority: number = 5): Promise<void> {
    if (!this.channel) {
      throw new Error('RabbitMQ channel not initialized');
    }

    const message = Buffer.from(JSON.stringify(job));
    
    await this.channel.sendToQueue(this.queueName, message, {
      persistent: true,
      priority,
      timestamp: Date.now(),
    });

    console.log(`Video compilation job published for request: ${job.requestId}`);
  }

  async getQueueStats(): Promise<{ messageCount: number; consumerCount: number }> {
    if (!this.channel) {
      throw new Error('RabbitMQ channel not initialized');
    }

    try {
      const queueInfo = await this.channel.checkQueue(this.queueName);
      return {
        messageCount: queueInfo.messageCount,
        consumerCount: queueInfo.consumerCount,
      };
    } catch (error) {
      console.error('Error getting queue stats:', error);
      return {
        messageCount: 0,
        consumerCount: 0,
      };
    }
  }

  async isHealthy(): Promise<boolean> {
    try {
      if (!this.connection || !this.channel) {
        return false;
      }
      
      await this.channel.checkQueue(this.queueName);
      return true;
    } catch (error) {
      console.error('Queue service health check failed:', error);
      return false;
    }
  }
}