#!/bin/bash
# Development startup script

set -e

echo "🚀 Starting Knowledge Base Development Environment..."

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

# Create .env if not exists
if [ ! -f "backend/.env" ]; then
    echo "📝 Creating .env file..."
    cp backend/.env.example backend/.env
    echo "✅ Created backend/.env"
fi

# Start services
echo "🐳 Starting Docker services..."
docker-compose up -d postgres redis minio etcd milvus-minio milvus

echo "⏳ Waiting for services to be ready..."
sleep 10

# Check services
echo "🔍 Checking service health..."
docker-compose ps

echo ""
echo "✅ Services are ready!"
echo ""
echo "📚 Service URLs:"
echo "  - PostgreSQL: localhost:5432"
echo "  - Redis:      localhost:6379"
echo "  - MinIO:      http://localhost:9000"
echo "  - Milvus:     localhost:19530"
echo ""
echo "To start the backend:"
echo "  cd backend && python -m uvicorn app.main:app --reload"
echo ""
echo "To start the frontend:"
echo "  cd frontend && npm run dev"
echo ""
echo "To stop services:"
echo "  docker-compose down"
