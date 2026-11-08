
import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

# Use a separate database when YOTTAFLEX_DATABASE_URL is provided.
# Otherwise, retain the existing application database.
DATABASE_URL = os.getenv(
    "YOTTAFLEX_DATABASE_URL",
    "sqlite:///./complaints.db"
)

# Create the database engine.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {}
)

# Enable foreign-key enforcement in SQLite.
if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# Create a reusable database session factory.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for all database models.
Base = declarative_base()


# Dependency for providing database sessions to API routes.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Import models so SQLAlchemy registers their tables.
import backend.app.models

# Create all registered database tables.
Base.metadata.create_all(bind=engine)
