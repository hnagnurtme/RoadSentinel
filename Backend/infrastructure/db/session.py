from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from infrastructure.db.models import Base
from shared.config import settings

DATABASE_URL = settings.DATABASE_URL

# For SQLite, need check_same_thread
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=settings.SQL_ECHO,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create database tables from models (for quick dev setup)."""
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
