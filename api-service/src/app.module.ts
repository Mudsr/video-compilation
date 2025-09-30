import { Module, Global } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { FramesModule } from './modules/frames/frames.module';
import { VideoModule } from './modules/video/video.module';
import { PrismaService } from './common/services/prisma.service';
import { QueueService } from './common/services/queue.service';
import { StorageService } from './common/services/storage.service';

@Global()
@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      envFilePath: '.env',
    }),
    FramesModule,
    VideoModule,
  ],
  providers: [
    PrismaService,
    QueueService,
    StorageService,
  ],
  exports: [
    PrismaService,
    QueueService,
    StorageService,
  ],
})
export class AppModule {}