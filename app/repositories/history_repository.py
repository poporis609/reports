"""
History 리포지토리 - 일기 데이터 조회
"""
from datetime import date
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.models.history import History


class HistoryRepository:
    """일기 데이터 리포지토리 (읽기 전용)"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_entries_by_user_and_period(
        self,
        user_id: str,
        start_date: date,
        end_date: date
    ) -> List[History]:
        """
        특정 사용자의 기간 내 일기 항목을 조회합니다.
        
        Args:
            user_id: 사용자 ID (Cognito sub)
            start_date: 시작 날짜
            end_date: 종료 날짜
            
        Returns:
            해당 기간의 일기 목록
        """
        stmt = select(History).where(
            and_(
                History.user_id == user_id,
                History.record_date >= start_date,
                History.record_date <= end_date
            )
        ).order_by(History.record_date)
        
        result = self.db.execute(stmt)
        return list(result.scalars().all())
    
    def get_user_entries_count(
        self,
        user_id: str,
        start_date: date,
        end_date: date
    ) -> int:
        """
        특정 사용자의 기간 내 일기 개수를 조회합니다.
        
        Args:
            user_id: 사용자 ID
            start_date: 시작 날짜
            end_date: 종료 날짜
            
        Returns:
            일기 개수
        """
        entries = self.get_entries_by_user_and_period(user_id, start_date, end_date)
        return len(entries)
    
    def get_entry_by_id(self, entry_id: int) -> Optional[History]:
        """
        ID로 일기 항목을 조회합니다.
        
        Args:
            entry_id: 일기 ID
            
        Returns:
            일기 항목 또는 None
        """
        stmt = select(History).where(History.id == entry_id)
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()
