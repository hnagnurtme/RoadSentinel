# RoadSentinel - Backend API

High-performance REST API built with FastAPI, PostgreSQL, and SQLAlchemy to support the RoadSentinel application.

## 🚀 Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **Migrations**: Alembic
- **Validation**: Pydantic v2
- **Auth**: JWT (OAuth2 with password flow)
- **Containerization**: Docker & Docker Compose

## 📁 Project Structure

```
Backend/
├── api/             # API Router and Endpoints (v1)
├── core/            # Application configuration & security
├── db/              # Database connection and base models
├── models/          # SQLAlchemy database models
├── schemas/         # Pydantic models for request/response
├── services/        # Business logic layer
├── migrations/      # Alembic migration scripts
├── middleware/      # Custom FastAPI middleware
├── tests/           # Unit and integration tests
└── main.py          # Application entry point
```

## 🛠️ Getting Started

### Prerequisites
- Python 3.10+
- PostgreSQL
- Docker (optional)

### Setup
1. **Clone and navigate**:
   ```bash
   cd Backend
   ```

2. **Setup virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables**:
   Copy `.env.example` to `.env` and fill in your details:
   ```bash
   cp .env.example .env
   ```

5. **Run Migrations**:
   ```bash
   alembic upgrade head
   ```

6. **Start Application**:
   ```bash
   uvicorn main:app --reload
   ```

### API Documentation
Once the server is running, you can access:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 🧪 Testing
Run tests using pytest:
```bash
pytest
```

## 🐋 Docker Support
Build and run the entire stack using Docker Compose from the root directory:
```bash
docker-compose up --build
```
