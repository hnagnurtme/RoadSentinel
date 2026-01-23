# RoadSentinel Docker Development Environment

This guide will help you set up the RoadSentinel application using Docker Compose for local development.

## Prerequisites

- Docker Desktop installed ([Download here](https://www.docker.com/products/docker-desktop))
- Docker Compose (included with Docker Desktop)

## Quick Start

### 1. Clone and Setup

```bash
cd RoadSentinel
cp .env.example .env
```

### 2. Start All Services

```bash
docker-compose -f docker-compose.dev.yml up --build
```

This will start:
- **PostgreSQL** database on port `5432`
- **Django Backend** on port `8000`
- **React Frontend** on port `5173`

### 3. Access the Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/swagger/
- **Django Admin**: http://localhost:8000/admin/

## Individual Service Commands

### Start specific service
```bash
docker-compose -f docker-compose.dev.yml up backend
docker-compose -f docker-compose.dev.yml up frontend
docker-compose -f docker-compose.dev.yml up db
```

### Stop all services
```bash
docker-compose -f docker-compose.dev.yml down
```

### Stop and remove volumes (cleans database)
```bash
docker-compose -f docker-compose.dev.yml down -v
```

## Database Management

### Run migrations
```bash
docker-compose -f docker-compose.dev.yml exec backend python manage.py migrate
```

### Create superuser
```bash
docker-compose -f docker-compose.dev.yml exec backend python manage.py createsuperuser
```

### Access PostgreSQL
```bash
docker-compose -f docker-compose.dev.yml exec db psql -U postgres -d roadsentinel_dev
```

## Development Workflow

### View logs
```bash
# All services
docker-compose -f docker-compose.dev.yml logs -f

# Specific service
docker-compose -f docker-compose.dev.yml logs -f backend
docker-compose -f docker-compose.dev.yml logs -f frontend
```

### Execute commands in containers
```bash
# Backend (Django)
docker-compose -f docker-compose.dev.yml exec backend python manage.py makemigrations
docker-compose -f docker-compose.dev.yml exec backend python manage.py shell

# Frontend (Node)
docker-compose -f docker-compose.dev.yml exec frontend npm install <package>
```

### Rebuild after dependency changes
```bash
docker-compose -f docker-compose.dev.yml up --build
```

## Troubleshooting

### Port already in use
If you get port conflicts, you can modify the ports in `docker-compose.dev.yml`:
```yaml
ports:
  - "8001:8000"  # Maps host 8001 to container 8000
```

### Reset database
```bash
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up -d db
docker-compose -f docker-compose.dev.yml exec backend python manage.py migrate
```

### Fresh start
```bash
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up --build
```

## Environment Variables

Key environment variables in `.env`:

```env
# Database
DATABASE_ENGINE=django.db.backends.postgresql
DATABASE_NAME=roadsentinel_dev
DATABASE_USER=postgres
DATABASE_PASSWORD=postgres
DATABASE_HOST=db
DATABASE_PORT=5432

# Django
DEBUG=True
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1,backend

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Frontend
VITE_API_URL=http://localhost:8000
```

## Notes

- Hot reloading is enabled for both backend and frontend
- Code changes will automatically reload the services
- Database data persists in Docker volumes
- Node modules are cached in volumes for faster builds
