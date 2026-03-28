# ReelForge AI 🎬

> The world's first zero-edit AI video director for short-form content.

Upload raw, unedited footage and photos. Get influencer-quality reels in 90 seconds. No editing skills required.

## 🏗️ Architecture

```
reelforge/
├── apps/
│   ├── api/          # FastAPI backend + Alembic migrations
│   └── web/          # Next.js 15 frontend
├── workers/          # 7 Celery workers
│   ├── ingest/       # Media transcoding & thumbnails
│   ├── scene/        # PySceneDetect scene detection
│   ├── scoring/      # GPT-4o Vision frame scoring
│   ├── audio/        # Librosa BPM + Whisper speech
│   ├── dna/          # Style DNA extraction
│   ├── blueprint/    # Claude blueprint generation
│   └── assembly/     # FFmpeg reel assembly
├── services/
│   ├── trend/        # Trend Pulse engine
│   └── notify/       # Notification service
├── shared/           # Shared Python packages
│   ├── config.py     # Central configuration
│   ├── models/       # SQLAlchemy ORM (8 tables)
│   ├── schemas/      # Pydantic models
│   ├── storage/      # Cloudflare R2 client
│   └── queue/        # Redis queue helpers
├── docker-compose.yml
└── alembic.ini
```

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 20+
- Python 3.12+

### Setup
```bash
# Clone the repo
git clone https://github.com/your-org/reelforge.git
cd reelforge

# Copy environment variables
cp .env.example .env
# Edit .env with your API keys (OpenAI, Anthropic, Supabase, etc.)

# Start all services
docker-compose up
```

### Access
- **Frontend**: http://localhost:3000
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 🔧 Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, React 19, Tailwind CSS 4, Framer Motion |
| State | Zustand, React Query |
| Auth | Supabase (JWT) |
| API | FastAPI (Python 3.12) |
| Database | PostgreSQL 16 + pgvector |
| Queue | Redis 7 + Celery 5 |
| AI | GPT-4o Vision, Claude 3.5 Sonnet, Whisper |
| Video | FFmpeg, PySceneDetect, OpenCV |
| Audio | Librosa, Whisper |
| Storage | Cloudflare R2 (S3-compatible) |
| Payments | Stripe |

## 🎯 Two Modes

### Clone Mode 🧬
Upload an inspiration reel → AI extracts Style DNA (pace, colour grade, transitions, BPM) → Get a shot list → Upload your media → AI recreates the same style.

### Auto-Create Mode ⚡
Dump raw footage → AI analyses, scores, and picks the best moments → Maps to trending reel structure → Produces a finished reel with professional edits.

## 📊 Pipeline Stages

1. **Ingest** — Transcode to H.264 1080p/30fps, generate thumbnails
2. **Scene Detection** — PySceneDetect content-aware segmentation
3. **Scoring** — GPT-4o Vision scores: sharpness, composition, lighting, energy
4. **Audio** — BPM detection, beat grid, speech-to-text via Whisper
5. **DNA Extraction** — (Clone mode) Cut pace, colour histogram, optical flow, OCR
6. **Blueprint** — Claude generates time-coded reel structure with slot matching
7. **Assembly** — FFmpeg renders with transitions, Ken Burns, text overlays, 3 format exports

## 💰 Pricing Tiers

| Tier | Price | Reels | Resolution | Features |
|------|-------|-------|------------|----------|
| Free | $0 | 3/mo | 720p | Auto-Create, Watermark |
| Creator | $12/mo | 30/mo | 1080p | Clone + Auto, No watermark |
| Pro | $29/mo | Unlimited | 4K | API access, 50GB vault |
| Studio | $99/mo | Unlimited | 4K | Team seats, White-label |

## 🌍 i18n Ready

Supports 8 languages: English, Hindi, Portuguese, Spanish, French, German, Arabic, Japanese.

## 📄 License

Proprietary. All rights reserved.
