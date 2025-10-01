import { Module, Global } from '@nestjs/common';
import { PrismaService } from './services/prisma.service';
import { QueueService } from './services/queue.service';
import { StorageService } from './services/storage.service';

@Global()
@Module({
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
export class CommonModule {}