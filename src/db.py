import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError

DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    # sensible default for local Postgres; update in .env
    DATABASE_URL = 'postgresql+asyncpg://postgres:1122@localhost:5432/newsdb'
else:
    # If DATABASE_URL is set but doesn't specify asyncpg, fix it
    if DATABASE_URL.startswith('postgresql://'):
        DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://', 1)
    elif DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql+asyncpg://', 1)

engine = create_async_engine(DATABASE_URL, future=True, echo=False)
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()


async def init_db():
    """Create DB tables (run once)."""
    from sqlalchemy import text
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ DB initialized")
    except SQLAlchemyError as e:
        print(f"❌ DB init failed: {e}")