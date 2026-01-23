# RoadSentinel Backend

Django REST Framework backend for RoadSentinel application.

## Project Structure

```
backend/
├── manage.py                         # Django entry point
├── config/                           # Global project configuration
│   ├── settings.py                   # Django settings
│   ├── urls.py                       # Root URL routing
│   ├── swagger.py                    # OpenAPI / Swagger configuration
│   └── wsgi.py
├── apps/                             # Application modules
│   ├── auth/                         # Authentication & authorization
│   └── user/                         # User profile management
├── middlewares/                      # Custom middlewares
│   ├── exception_middleware.py       # Global exception handling
│   ├── logging_middleware.py         # Request/response logging
│   └── timing_middleware.py          # Performance tracking
├── shared/                           # Shared utilities
│   ├── responses/                    # API response formatting
│   ├── exceptions.py                 # Custom exceptions
│   └── utils.py                      # Helper functions
└── requirements.txt                  # Dependencies
```

## Setup Instructions

### 1. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate   # On Windows
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment Configuration

Copy `.env.example` to `.env` and update with your settings:

```bash
cp .env.example .env
```

### 4. Database Setup

```bash
# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### 5. Run Development Server

```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, you can access:

- **Swagger UI**: http://localhost:8000/swagger/
- **ReDoc**: http://localhost:8000/redoc/
- **Admin Panel**: http://localhost:8000/admin/

## API Endpoints

### Authentication
- `POST /api/auth/register/` - User registration
- `POST /api/auth/login/` - User login
- `POST /api/auth/refresh/` - Refresh access token

### User Profile
- `GET /api/user/profile/` - Get user profile
- `PUT /api/user/profile/` - Update user profile

## Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=apps --cov-report=html
```

## Code Quality

```bash
# Format code
black .

# Lint code
flake8
```

## Technologies Used

- **Django 5.0** - Web framework
- **Django REST Framework** - REST API toolkit
- **Simple JWT** - JWT authentication
- **drf-yasg** - API documentation
- **PostgreSQL** - Database (optional, SQLite by default)

## License

MIT
