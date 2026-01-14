"""
User 모델 - 기존 사용자 테이블 (읽기 전용)
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    """
    사용자 테이블 (기존 테이블, 읽기 전용)
    
    Attributes:
        user_id: 사용자 ID (Cognito sub, PK)
        email: 이메일
        nickname: 닉네임
        status: 상태
        created_at: 생성 시간
        updated_at: 수정 시간
        deleted_at: 삭제 시간 (soft delete)
    """
    __tablename__ = "users"
    
    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    nickname: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    def __repr__(self) -> str:
        return f"<User(user_id={self.user_id}, nickname={self.nickname})>"
    
    @property
    def is_active(self) -> bool:
        """사용자가 활성 상태인지 확인"""
        return self.deleted_at is None
