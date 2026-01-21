@echo off
REM Development startup script for Windows

echo Starting Knowledge Base Development Environment...

REM Check Docker
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Docker not found. Please install Docker Desktop first.
    exit /b 1
)

REM Create .env if not exists
if not exist "backend\.env" (
    echo Creating .env file...
    copy backend\.env.example backend\.env
    echo Created backend\.env
)

REM Start services
echo Starting Docker services...
docker-compose up -d postgres redis minio etcd milvus-minio milvus

echo Waiting for services to be ready...
timeout /t 10 /nobreak >nul

REM Check services
echo Checking service health...
docker-compose ps

echo.
echo Services are ready!
echo.
echo Service URLs:
echo   - PostgreSQL: localhost:5432
echo   - Redis:      localhost:6379
echo   - MinIO:      http://localhost:9000
echo   - Milvus:     localhost:19530
echo.
echo To start the backend:
echo   cd backend ^&^& python -m uvicorn app.main:app --reload
echo.
echo To start the frontend:
echo   cd frontend ^&^& npm run dev
echo.
echo To stop services:
echo   docker-compose down
