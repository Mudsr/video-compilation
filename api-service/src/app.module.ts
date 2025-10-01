import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { FramesModule } from './modules/frames/frames.module';
import { VideoModule } from './modules/video/video.module';
import { CommonModule } from './common/common.module';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      envFilePath: '.env',
    }),
    FramesModule,
    VideoModule,
    CommonModule
  ],
})
export class AppModule {}