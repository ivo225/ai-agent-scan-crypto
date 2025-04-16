import os
import logging # Import logging
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

# Configure logging to silence SQLAlchemy engine logs unless they are warnings or errors
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./crypto_analysis.db")

# Set echo=False to disable SQL query logging by default, logging config above handles levels
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)
Base = declarative_base()

async def get_db() -> AsyncSession:
    """
    Dependency function that yields an async database session.
    """
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():
    """
    Initialize the database by creating all tables.
    WARNING: This will drop existing tables first.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all) # Drop existing tables
        await conn.run_sync(Base.metadata.create_all) # Create tables with new schema
