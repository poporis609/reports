"""
데이터베이스 연결 설정
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.config.settings import get_settings

settings = get_settings()

# SQLAlchemy 엔진 생성
engine = create_engine(
    settings.get_database_url(),
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

# 세션 팩토리
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """데이터베이스 세션을 생성하고 반환합니다."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
