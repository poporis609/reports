"""
History 모델 - 기존 일기 테이블 (읽기 전용)
"""
from datetime import date
from typing import Optional, List
from sqlalchemy import BigInteger, String, Text, Date, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class History(Base):
    """
    일기 기록 테이블 (기존 테이블, 읽기 전용)
    
    Attributes:
        id: 일기 ID (PK)
        user_id: 사용자 ID (Cognito sub)
        content: 일기 내용
        record_date: 작성 날짜
        tags: 태그 목록 (활동, 날씨 등)
        s3_key: S3 파일 키
        text_url: 텍스트 URL
    """
    __tablename__ = "history"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    tags: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), nullable=True)
    s3_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    text_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    def __repr__(self) -> str:
        return f"<History(id={self.id}, user_id={self.user_id}, record_date={self.record_date})>"
