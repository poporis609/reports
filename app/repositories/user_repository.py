"""
User 리포지토리 - 사용자 데이터 조회
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.user import User


class UserRepository:
    """사용자 데이터 리포지토리 (읽기 전용)"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        사용자 ID로 사용자를 조회합니다.
        
        Args:
            user_id: 사용자 ID (Cognito sub)
            
        Returns:
            사용자 또는 None
        """
        stmt = select(User).where(User.user_id == user_id)
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    def get_user_by_nickname(self, nickname: str) -> Optional[User]:
        """
        닉네임으로 사용자를 조회합니다.
        
        Args:
            nickname: 닉네임
            
        Returns:
            사용자 또는 None
        """
        stmt = select(User).where(
            User.nickname == nickname,
            User.deleted_at.is_(None)  # 삭제되지 않은 사용자만
        )
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    def get_active_users(self) -> List[User]:
        """
        활성 상태의 모든 사용자를 조회합니다.
        
        Returns:
            활성 사용자 목록
        """
        stmt = select(User).where(User.deleted_at.is_(None))
        result = self.db.execute(stmt)
        return list(result.scalars().all())
