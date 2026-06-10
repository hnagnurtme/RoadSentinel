# 🚗 RoadSentinel — AI-Powered Driver Monitoring Backend

> Real-time driver behaviour analysis using YOLOv8, FastAPI, and WebSocket streaming.  
> Detects sleeping, phone usage, distraction, and drowsiness — then records annotated video evidence and persists alerts automatically.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
  - [Layer Overview](#layer-overview)
  - [AI Processing Pipeline](#ai-processing-pipeline)
  - [WebSocket Flow](#websocket-flow)
- [Project Structure](#project-structure)
- [Domain Model](#domain-model)
- [REST API Endpoints](#rest-api-endpoints)
- [WebSocket Endpoints](#websocket-endpoints)
- [Configuration](#configuration)
  - [Environment Variables (.env)](#environment-variables-env)
  - [config.yaml (non-secret defaults)](#configyaml-non-secret-defaults)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Local Development](#local-development)
  - [Docker](#docker)
- [Database Migrations](#database-migrations)
- [AI Model](#ai-model)
  - [Detection Labels](#detection-labels)
  - [Event Classification](#event-classification)
  - [Driver Safety State Machine](#driver-safety-state-machine)
- [Evidence Pipeline](#evidence-pipeline)
- [Alert Decision Engine](#alert-decision-engine)
- [Development Commands (just)](#development-commands-just)

---

## Overview

RoadSentinel Backend is a **Python / FastAPI** service that processes live camera frames from an **ESP32-CAM** device, runs YOLOv8 inference to detect dangerous driver behaviours, and pushes real-time alerts to browser dashboards via WebSocket.

Key capabilities:
- 🤖 **YOLOv8 inference** with batch support and adaptive frame-skipping
- 🧠 **Multi-level event classifier** with hysteresis counters and sliding-window scoring
- 🚦 **Driver Safety State Machine** — NORMAL → DROWSY → DANGEROUS → CRITICAL
- 🎬 **Annotated MP4 evidence clips** saved locally and/or uploaded to Cloudinary
- 📡 **Three WebSocket channels** — ESP32-CAM feed, browser viewer, alert dashboard
- 🗄 **PostgreSQL + SQLAlchemy 2** with full Alembic migration support
- 🏛 **Clean Architecture** — domain / application / infrastructure / interfaces layers

---

## Architecture

### Layer Overview

```
┌────────────────────────────────────────────────────────────┐
│              interfaces/api  (FastAPI routes)               │
│   REST: /users  /vehicles  /alerts                         │
│   WS:   /ws/camera  /ws/frontend  /ws/alerts               │
├────────────────────────────────────────────────────────────┤
│                   application layer                         │
│   Commands & Queries (CQRS) + DTOs per domain              │
│   alert │ user │ vehicle                                    │
├────────────────────────────────────────────────────────────┤
│                    domain layer                             │
│   Entities · Value Objects · Repository interfaces         │
│   alert │ user │ vehicle                                    │
├────────────────────────────────────────────────────────────┤
│                infrastructure layer                         │
│   SQLAlchemy models · Repository implementations           │
│   Alembic migrations · DB session                          │
├────────────────────────────────────────────────────────────┤
│                     core/ai layer                           │
│   YOLOInferenceEngine · DriverEventClassifier              │
│   DriverStateMachine · AlertDecisionEngine                 │
│   DriverEvidencePipeline · AnnotatorHelper                 │
└────────────────────────────────────────────────────────────┘
```

### AI Processing Pipeline

Each JPEG frame received from the ESP32-CAM goes through the following pipeline:

```
ESP32-CAM (JPEG)
       │
       ▼
 CameraFrameProcessor.process_frame()
       │
       ├─ Adaptive frame-skip check (skip every N frames when idle)
       │
       ├─ YOLOInferenceEngine.run_inference()
       │      └─ decode JPEG → resize to 320×240 → YOLOv8 → scale bbox back
       │
       ├─ filter_detections()  ← keep only RELEVANT_CLASSES, sort by conf
       │
       ├─ DriverEventClassifier.classify()
       │      ├─ Map raw YOLO labels → events (sleeping/drowsy/using_phone/distracted)
       │      ├─ L1/L2/L3 sliding-window composite scores with exponential decay
       │      ├─ Hysteresis counters (enter / exit / hold / candidate streaks)
       │      ├─ Fast-path promotion on high-confidence detections
       │      └─ Returns (event, confidence, active_events[])
       │
       ├─ Drowsy escalation check (drowsy ≥ DROWSY_ESCALATION_SECONDS → escalated=True)
       │
       ├─ WindowTrigger (rolling occupancy) → decide save_evidence flag
       │
       ├─ Grace-period trackers → suppress lower-priority events briefly
       │
       └─ FrameResult(event, confidence, escalated, detections,
                       should_broadcast, should_save_evidence, all_events)
              │
              ├─ If should_save_evidence → DriverEvidencePipeline.save_event_alert()
              │      ├─ Encode annotated MP4 clip from rolling frame buffer
              │      ├─ Upload to Cloudinary (optional)
              │      └─ Persist AlertEntity to PostgreSQL
              │
              └─ If should_broadcast → broadcast JSON via WebSocket to browser viewers
```

### WebSocket Flow

```
ESP32-CAM ──WS /ws/camera──► Backend
                                │
                                ├─► AI pipeline (per frame)
                                │
                                ├─► FrontendManager.send_raw_frame()  (JPEG binary)
                                │
                                └─► FrontendManager.broadcast()       (JSON events)

Browser ──WS /ws/frontend──► Backend
  │  ping/pong, camera commands (set_quality, set_framesize…)

Dashboard ──WS /ws/alerts──► Backend
  │  receives alert.created / alert.deleted events (JSON)
```

---

## Project Structure

```
Backend/
├── main.py                        # FastAPI app factory, lifespan (model load)
├── config.yaml                    # Non-secret application defaults (YAML)
├── .env                           # Secret env vars (DATABASE_URL, Cloudinary keys)
├── .env.example                   # Template for .env
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── justfile                       # Developer task runner
├── alembic/                       # DB migrations
│   └── versions/
│
├── core/
│   └── ai/
│       ├── engine.py              # YOLOInferenceEngine + filter_detections()
│       ├── event_classifier.py    # DriverEventClassifier + WindowTrigger
│       ├── driver_state_machine.py# DriverStateMachine (NORMAL→CRITICAL)
│       ├── alert_decision_engine.py# AlertDecisionEngine (rules + cooldown)
│       ├── evidence_pipeline.py   # DriverEvidencePipeline (clip + upload + DB)
│       ├── evidence_buffer.py     # Rolling frame buffer
│       ├── annotator.py           # OpenCV bbox/label overlay on evidence frames
│       ├── frame_processing_pipeline.py
│       ├── temporal_reasoning.py  # EWMA confidence smoothing
│       ├── detection_normaliser.py
│       └── performance_monitor.py # FPS / latency metrics
│
├── domain/
│   ├── alert/
│   │   ├── entities.py            # AlertEntity
│   │   ├── value_objects.py       # AlertType enum, Position
│   │   ├── repository.py          # IAlertRepository interface
│   │   └── services.py
│   ├── user/
│   │   ├── entities.py
│   │   ├── value_objects.py
│   │   ├── repository.py
│   │   └── services.py
│   └── vehicle/
│       ├── entities.py
│       ├── repository.py
│       └── services.py
│
├── application/
│   ├── alert/
│   │   ├── alert_dto.py
│   │   ├── commands/              # CreateAlert, DeleteAlert handlers
│   │   └── queries/               # GetAlert, ListAlertsOverview handlers
│   ├── user/
│   │   ├── user_dto.py
│   │   ├── commands/
│   │   └── queries/
│   └── vehicle/
│       ├── vehicle_dto.py
│       ├── commands/
│       └── queries/
│
├── infrastructure/
│   ├── db/
│   │   ├── session.py             # SQLAlchemy engine + SessionLocal
│   │   └── models/                # ORM models (Alert, User, Vehicle, Views)
│   └── repositories/
│       ├── alert_repository_impl.py
│       ├── user_repository_impl.py
│       └── vehicle_repository_impl.py
│
├── interfaces/
│   └── api/
│       ├── deps.py                # FastAPI dependency injection
│       ├── response.py            # Unified success_response() helper
│       ├── middleware/
│       │   ├── auth.py
│       │   └── exception.py       # Global exception handlers
│       └── v1/
│           ├── alert.py           # POST/GET/DELETE /alerts
│           ├── user.py            # POST/GET /users
│           ├── vehicle.py         # POST/GET /vehicles
│           ├── websocket.py       # WS /camera /frontend /alerts
│           ├── camera_processor.py# CameraFrameProcessor (per-session AI state)
│           └── mappers.py         # Entity → Pydantic response mappers
│
├── shared/
│   ├── config.py                  # Pydantic Settings (env + yaml merged)
│   └── exceptions.py
│
├── evidence/                      # Local MP4 evidence clips (mounted as /evidence)
└── tests/
    └── test_alert_type_sync.py
```

---

## Domain Model

| Entity | Key Fields |
|--------|-----------|
| `AlertEntity` | `message`, `alert_type` (SLEEPING/USING_PHONE/DISTRACTED), `device_id`, `driver_id?`, `vehicle_id?`, `evidence_url?`, `latitude?`, `longitude?` |
| `UserEntity` | `email`, `name`, `avatar_image_url`, address fields, `birthday`, `gender` |
| `VehicleEntity` | `plate_number`, `manufacturer`, `model`, `color`, `production_year`, `vin` |

`AlertType` enum values:

| Value | Trigger |
|-------|---------|
| `SLEEPING` | Eyes closed detected OR drowsy escalated |
| `USING_PHONE` | Mobile phone in hand |
| `DISTRACTED` | Looking away, reaching behind / distracted, drinking, seat belt |

---

## REST API Endpoints

Base path: `/api/v1`

### Alerts

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/alerts` | Create a manual alert |
| `GET` | `/alerts` | List alerts (`?limit=20&driver_id=<uuid>`) |
| `GET` | `/alerts/{id}` | Get single alert with user/vehicle resolved |
| `DELETE` | `/alerts/{id}` | Soft-delete an alert; broadcasts `alert.deleted` |

### Users

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/users` | Create a driver/user profile |
| `GET` | `/users` | List all users |
| `GET` | `/users/{id}` | Get single user |

### Vehicles

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/vehicles` | Register a vehicle |
| `GET` | `/vehicles` | List vehicles (`?limit=20`) |
| `GET` | `/vehicles/{id}` | Get single vehicle |

### Health

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Health check — returns `{"status": "ok"}` |

Interactive docs available at **`/docs`** (Swagger UI) and **`/redoc`**.

---

## WebSocket Endpoints

| Path | Direction | Description |
|------|-----------|-------------|
| `ws://host/ws/camera` | ESP32 → Server | Raw JPEG frame stream + pong stats |
| `ws://host/api/v1/ws/frontend` | Browser ↔ Server | Receives JPEG frames + JSON events; sends camera control commands |
| `ws://host/api/v1/ws/alerts` | Server → Dashboard | Broadcasts `alert.created` / `alert.deleted` JSON events |

### Frontend WebSocket Messages (Server → Browser)

```jsonc
// Raw JPEG frame (binary)
<binary bytes>

// Detection result
{
  "type": "frame",
  "frame_idx": 1024,
  "detections": [{"label": "mobile", "conf": 0.87, "bbox": [x1,y1,x2,y2]}],
  "event": "using_phone",
  "confidence": 0.87,
  "event_timing": {"active": true, "event": "using_phone", "duration_ms": 4200, "confidence": 0.87},
  "timestamp": 12345.678
}

// Driver danger event
{
  "type": "driver_event",
  "event": "sleeping",
  "confidence": 0.92,
  "drowsy_duration": 0.0,
  "escalated": false
}

// Alert persisted to DB
{
  "type": "alert_created",
  "data": { /* AlertEntity serialised */ }
}

// ESP32 stats
{ "type": "esp32_stats", "fps": 15.2, "heap": 32768 }
```

### Frontend WebSocket Commands (Browser → Server)

```jsonc
{ "type": "ping" }
{ "type": "set_quality", "value": 10 }
{ "type": "set_framesize", "value": "SVGA" }
{ "type": "set_vflip", "value": true }
{ "type": "set_hmirror", "value": false }
```

---

## Configuration

Settings are resolved in the following **priority order** (highest wins):

1. Environment variables (shell / `.env` file)  
2. `config.yaml` (non-secret defaults, flattened to `UPPER_SNAKE_CASE`)  
3. Pydantic `Settings` field defaults

> **Never put secrets** (`DATABASE_URL`, `CLOUDINARY_API_KEY/SECRET`) in `config.yaml`. Use `.env` or CI secrets.

### Environment Variables (.env)

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | `RoadSentinel Backend` | Application name (OpenAPI title) |
| `APP_ENV` | `development` | Environment name |
| `APP_HOST` | `127.0.0.1` | Uvicorn bind host |
| `APP_PORT` | `8000` | Uvicorn bind port |
| `APP_PUBLIC_BASE_URL` | `http://127.0.0.1:8000` | Base URL used for evidence local URLs |
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/roadsentinel` | PostgreSQL connection string |
| `SQL_ECHO` | `false` | Log SQL statements |
| `CORS_ALLOW_ORIGINS` | `http://localhost:3000,...` | Comma-separated CORS origins |

#### AI / Driver Event Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DRIVER_EVENT_SLEEP_ENTER_FRAMES` | `2` | Frames of eyes-closed evidence to confirm sleeping |
| `DRIVER_EVENT_SLEEP_EXIT_FRAMES` | `1` | Frames without evidence to exit sleeping state |
| `DRIVER_EVENT_PHONE_ENTER_FRAMES` | `3` | Frames to confirm phone usage |
| `DRIVER_EVENT_DISTRACTED_ENTER_FRAMES` | `6` | Frames for distraction (brief glances are normal) |
| `DRIVER_EVENT_DROWSY_ENTER_FRAMES` | `4` | Frames to confirm drowsiness |
| `DRIVER_EVENT_DROWSY_ESCALATION_SECONDS` | `10.0` | Seconds of drowsy → escalate to sleeping urgency |
| `DRIVER_EVENT_ALERT_COOLDOWN_SECONDS` | `3.0` | Min gap between repeated alerts for same event |
| `DRIVER_EVENT_MIN_SLEEP_CONFIDENCE` | `0.5` | Min YOLO confidence to count as sleeping evidence |
| `DRIVER_EVENT_MIN_PHONE_CONFIDENCE` | `0.6` | Min YOLO confidence for phone |
| `DRIVER_EVENT_L1_WINDOW_FRAMES` | `3` | Short-term scoring window |
| `DRIVER_EVENT_L2_WINDOW_FRAMES` | `9` | Mid-term scoring window |
| `DRIVER_EVENT_L3_WINDOW_FRAMES` | `24` | Long-term scoring window |
| `DRIVER_EVENT_WINDOW_DECAY` | `0.82` | Exponential weight decay per frame age |

#### Evidence & Cloudinary

| Variable | Default | Description |
|----------|---------|-------------|
| `DRIVER_EVENT_EVIDENCE_ENABLED` | `true` | Enable/disable clip recording |
| `DRIVER_EVENT_EVIDENCE_SECONDS` | `10` | Rolling buffer duration in seconds |
| `DRIVER_EVENT_EVIDENCE_FPS` | `5` | Frames per second of evidence clip |
| `DRIVER_EVENT_EVIDENCE_CODEC` | `mp4v` | Primary video codec (4-char FOURCC) |
| `DRIVER_EVENT_EVIDENCE_CODEC_CANDIDATES` | `avc1,H264,mp4v` | Codec fallback order |
| `DRIVER_EVENT_CLOUDINARY_ENABLED` | `false` | Upload clips to Cloudinary |
| `DRIVER_EVENT_CLOUDINARY_CLOUD_NAME` | _(empty)_ | Cloudinary cloud name |
| `DRIVER_EVENT_CLOUDINARY_API_KEY` | _(empty)_ | Cloudinary API key (secret!) |
| `DRIVER_EVENT_CLOUDINARY_API_SECRET` | _(empty)_ | Cloudinary API secret (secret!) |
| `DRIVER_EVENT_CLOUDINARY_FOLDER` | `roadsentinel/backend` | Upload folder in Cloudinary |

#### Fallback IDs (development only)

| Variable | Description |
|----------|-------------|
| `DRIVER_EVENT_FALLBACK_DEVICE_ID` | UUID used as `device_id` when no handshake context |
| `DRIVER_EVENT_FALLBACK_DRIVER_ID` | UUID for `driver_id` fallback |
| `DRIVER_EVENT_FALLBACK_VEHICLE_ID` | UUID for `vehicle_id` fallback |

### config.yaml (non-secret defaults)

`config.yaml` is flattened into environment variables using underscore joining. For example:

```yaml
driver_event:
  evidence:
    fps: 5
```

becomes `DRIVER_EVENT_EVIDENCE_FPS=5`. Values already set in the environment (or `.env`) are **not** overwritten.

---

## Getting Started

### Prerequisites

- Python 3.13+
- PostgreSQL 15+
- [`just`](https://github.com/casey/just) (optional but recommended)
- FFmpeg with h264 support (optional, for `avc1`/`H264` codec)
- YOLOv8 model file at `../AI/model/best.pt` relative to the backend root

### Local Development

```bash
# 1. Clone and enter backend directory
cd Backend/

# 2. Create virtualenv and install dependencies
just setup
# or manually:
python3.13 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env — set DATABASE_URL and any secrets

# 4. Run database migrations
just upgrade

# 5. Start the dev server (with hot-reload)
just run
# → http://127.0.0.1:8000
# → http://127.0.0.1:8000/docs
```

### Docker

```bash
# Build and start the backend container
docker compose up --build

# With custom env
APP_ENV=production DATABASE_URL=postgresql://... docker compose up
```

The container exposes port **8000** and mounts a `backend_data` volume.  
A health check polls `GET /` every 30 seconds.

---

## Database Migrations

Alembic is used for schema versioning. Common commands (all wrapped in `justfile`):

```bash
just migrate "add evidence_url column"  # autogenerate migration
just migrate-empty "manual migration"   # empty migration shell
just migrate-views "refresh views"      # regenerate Postgres views
just upgrade                            # apply all pending migrations
just downgrade                          # rollback one revision
just current                            # show current revision
just stamp head                         # stamp without running migrations
```

---

## AI Model

Place your YOLOv8 model at:

```
RoadSentinel/
├── AI/
│   └── model/
│       └── best.pt       ← YOLOv8 weights
└── Backend/
    └── ...
```

The model is loaded asynchronously on startup via `asyncio.to_thread()`.  
Inference runs at **320×240** resolution (configurable via `INFER_W`/`INFER_H` in `core/ai/engine.py`) with a confidence threshold of **0.2**.

### Detection Labels

The model outputs 7 relevant classes:

| YOLO Label | Maps to Event |
|------------|--------------|
| `eyes closed` | `sleeping` |
| `yawning` | `drowsy` |
| `mobile` | `using_phone` |
| `looking away` | `distracted` |
| `reaching behind` | `distracted` |
| `distracted` | `distracted` |
| `drinking` | `distracted` |
| `seat belt` | `distracted` |

### Event Classification

`DriverEventClassifier` maintains **per-event state** using a multi-layer scoring system:

1. **L1/L2/L3 sliding windows** — short (3 frames), medium (9), long (24) with exponential decay weight `0.82`  
2. **Composite score** — weighted sum: `0.45×L1 + 0.40×L2 + 0.15×L3` → value in `[0, 1]`  
3. **Hysteresis state machine** per event: `idle → candidate → confirmed → held → releasing`
4. **Fast-path promotion** — if confidence ≥ fastpath threshold (e.g. 0.80 for phone), immediately confirm without waiting for the window

Event priority (highest danger wins when multiple are active):

```
using_phone > sleeping > distracted > drowsy
```

**Drowsy escalation**: if `drowsy` has been continuously active for ≥ `DRIVER_EVENT_DROWSY_ESCALATION_SECONDS` (default 10s), `escalated=True` is returned, and the alert is treated with sleeping-level urgency.

### Driver Safety State Machine

`DriverStateMachine` maps event scores to a safety level:

| Safety State | Condition |
|---|---|
| `UNKNOWN` | No detections for ≥ 5 seconds |
| `NORMAL` | No hazardous events active |
| `DROWSY` | Drowsy active OR distracted briefly |
| `DANGEROUS` | Sleeping / phone active OR drowsy escalated OR distracted prolonged |
| `CRITICAL` | Sleeping ≥ 5s, phone ≥ 10s, distracted ≥ 20s |

State downgrades are held for `exit_hold_seconds` (default 3s) to prevent rapid flickering.

---

## Evidence Pipeline

When `WindowTrigger` fires (≥ 90% event occupancy over the rolling window), `DriverEvidencePipeline.save_event_alert()` is called **asynchronously** in the background:

1. **Encode MP4 clip** from the rolling `deque` (up to 10 seconds of annotated frames)
2. **Annotate frames** with bounding boxes, event label, confidence, and duration overlay (`annotator.py`)
3. **Upload to Cloudinary** (if enabled) and get a secure URL; otherwise serve locally at `/evidence/<filename>`
4. **Persist `AlertEntity`** to PostgreSQL via `CreateAlertHandler`
5. **Broadcast** the saved alert JSON to all connected dashboards via `alerts_ws_manager`

Evidence clips are stored in `./evidence/` (Docker volume: `backend_data`).  
Local clips are served as static files at `/evidence/<filename>`.

---

## Alert Decision Engine

`AlertDecisionEngine` applies business rules before generating an alert:

| Rule | Description |
|------|-------------|
| 1. Safe state | No alert if `NORMAL` or `UNKNOWN` |
| 2. Cooldown | No repeat alert within cooldown period (e.g. sleeping: 60s) |
| 3. Stable duration | Event must be active for `min_stable_seconds` (e.g. phone: 2s) |
| 4. Identified driver | Optionally require a known `driver_id` |
| 5. Severity mapping | `DROWSY` → `INFO`, `DANGEROUS` → `WARNING`, `CRITICAL` → `CRITICAL` |
| 6. Evidence | Save clip for `WARNING` and `CRITICAL` |
| 7. Device command | Send buzzer command to ESP32 for `CRITICAL` |

---

## Development Commands (just)

```bash
just setup          # Create venv and install dependencies
just install        # Reinstall dependencies only
just run            # Start uvicorn dev server with --reload
just migrate        # Autogenerate Alembic migration
just migrate-views  # Regenerate Postgres view migrations
just upgrade        # Apply all pending migrations (alembic upgrade head)
just downgrade      # Rollback one step (alembic downgrade -1)
just current        # Show current migration head
just stamp head     # Stamp DB without running migrations
just init-db        # Initialize DB tables directly (dev only)
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Web framework | FastAPI 0.116 + Uvicorn 0.35 |
| AI inference | YOLOv8 (Ultralytics ≥ 8.0) + OpenCV |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic 1.16 |
| Database | PostgreSQL 15 |
| Validation | Pydantic v2 / pydantic-settings |
| Video encoding | OpenCV VideoWriter (mp4v / avc1 / H264) |
| Cloud storage | Cloudinary SDK |
| Config | python-dotenv + PyYAML |
| Runtime | Python 3.13 |
| Container | Docker (python:3.13-slim) |

---

> _RoadSentinel — Keeping drivers safe, one frame at a time._
