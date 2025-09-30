-- CreateTable
CREATE TABLE "video_requests" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "requestId" TEXT NOT NULL,
    "totalFrames" INTEGER NOT NULL,
    "framesReceived" INTEGER NOT NULL DEFAULT 0,
    "status" TEXT NOT NULL DEFAULT 'pending',
    "outputFormat" TEXT NOT NULL DEFAULT 'mp4',
    "fps" INTEGER NOT NULL DEFAULT 30,
    "quality" TEXT NOT NULL DEFAULT 'medium',
    "videoUrl" TEXT,
    "errorMessage" TEXT,
    "compilationTime" REAL,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    "completedAt" DATETIME
);

-- CreateTable
CREATE TABLE "frames" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "requestId" TEXT NOT NULL,
    "frameNumber" INTEGER NOT NULL,
    "frameUrl" TEXT NOT NULL,
    "filename" TEXT NOT NULL,
    "uploadedAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "frames_requestId_fkey" FOREIGN KEY ("requestId") REFERENCES "video_requests" ("requestId") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateIndex
CREATE UNIQUE INDEX "video_requests_requestId_key" ON "video_requests"("requestId");

-- CreateIndex
CREATE UNIQUE INDEX "frames_requestId_frameNumber_key" ON "frames"("requestId", "frameNumber");
