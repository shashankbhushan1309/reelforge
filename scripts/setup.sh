#!/bin/bash
# ReelForge AI — Development setup script

echo "🎬 ReelForge AI — Setting up development environment"
echo "=================================================="

# Copy environment file
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Created .env from .env.example"
    echo "⚠️  Please update .env with your API keys"
fi

# Install Python dependencies
echo ""
echo "📦 Installing Python dependencies..."
pip install -r apps/api/requirements.txt
pip install -r workers/requirements.txt

# Install frontend dependencies
echo ""
echo "📦 Installing frontend dependencies..."
cd apps/web && npm install && cd ../..

echo ""
echo "✅ Development setup complete!"
echo ""
echo "To start the full stack:"
echo "  docker-compose up"
echo ""
echo "Or run services individually:"
echo "  cd apps/web && npm run dev     # Frontend on :3000"
echo "  uvicorn apps.api.main:app      # API on :8000"
echo "  celery -A workers.celery_app worker -Q reelforge:ingest"
