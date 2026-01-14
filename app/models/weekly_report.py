"""
WeeklyReport 모델 - 주간 리포트 테이블 (신규 생성)
"""
from datetime import date, datetime
from typing import List, Dict, Any
from sqlalchemy import Integer, String, Date, DateTime, Numeric, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class WeeklyReport(Base):
    """
    주간 리포트 테이블 (신규 생성)
    
    Attributes:
        id: 리포트 ID (PK, auto increment)
        user_id: 사용자 ID (FK -> users.user_id)
        nickname: 작성 시점의 닉네임
        week_start: 분석 시작일 (월요일)
        week_end: 분석 종료일 (일요일)
        average_score: 주간 평균 점수 (1-10)
        evaluation: 평가 유형 ('positive' | 'negative')
        daily_analysis: 일별 분석 결과 (JSONB)
        patterns: 패턴 분석 결과 (JSONB)
        feedback: 피드백 목록 (JSONB)
        created_at: 생성 시간
    """
    __tablename__ = "weekly_reports"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    nickname: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    week_end: Mapped[date] = mapped_column(Date, nullable=False)
    average_score: Mapped[float] = mapped_column(Numeric(3, 1), nullable=False)
    evaluation: Mapped[str] = mapped_column(String(20), nullable=False)
    daily_analysis: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    patterns: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    feedback: Mapped[List[str]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    
    __table_args__ = (
        CheckConstraint(
            "evaluation IN ('positive', 'negative')",
            name="check_evaluation_type"
        ),
    )
    
    def __repr__(self) -> str:
        return f"<WeeklyReport(id={self.id}, user_id={self.user_id}, week={self.week_start}~{self.week_end})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """리포트를 딕셔너리로 변환"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "nickname": self.nickname,
            "week_start": self.week_start.isoformat(),
            "week_end": self.week_end.isoformat(),
            "average_score": float(self.average_score),
            "evaluation": self.evaluation,
            "daily_analysis": self.daily_analysis,
            "patterns": self.patterns,
            "feedback": self.feedback,
            "created_at": self.created_at.isoformat(),
        }
