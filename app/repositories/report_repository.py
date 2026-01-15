"""
Report 리포지토리 - 주간 리포트 CRUD
"""
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.models.weekly_report import WeeklyReport


class ReportRepository:
    """주간 리포트 리포지토리"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def save_report(
        self,
        user_id: str,
        nickname: str,
        week_start: date,
        week_end: date,
        average_score: float,
        evaluation: str,
        daily_analysis: List[Dict[str, Any]],
        patterns: List[Dict[str, Any]],
        feedback: List[str],
        s3_key: Optional[str] = None,
        status: str = "completed"
    ) -> WeeklyReport:
        """
        새 주간 리포트를 저장합니다.
        
        Args:
            user_id: 사용자 ID
            nickname: 닉네임
            week_start: 주 시작일
            week_end: 주 종료일
            average_score: 평균 점수
            evaluation: 평가 유형 ('positive' | 'negative')
            daily_analysis: 일별 분석 결과
            patterns: 패턴 분석 결과
            feedback: 피드백 목록
            s3_key: S3 저장 경로
            status: 상태 ('processing' | 'completed' | 'failed')
            
        Returns:
            저장된 리포트
        """
        report = WeeklyReport(
            user_id=user_id,
            nickname=nickname,
            week_start=week_start,
            week_end=week_end,
            average_score=average_score,
            evaluation=evaluation,
            daily_analysis=daily_analysis,
            patterns=patterns,
            feedback=feedback,
            s3_key=s3_key,
            status=status,
            created_at=datetime.utcnow()
        )
        
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        
        return report
    
    def update_report(
        self,
        report_id: int,
        average_score: float,
        evaluation: str,
        daily_analysis: List[Dict[str, Any]],
        patterns: List[Dict[str, Any]],
        feedback: List[str],
        s3_key: Optional[str] = None,
        status: str = "completed"
    ) -> Optional[WeeklyReport]:
        """
        리포트를 업데이트합니다.
        """
        report = self.get_report_by_id(report_id)
        if not report:
            return None
        
        report.average_score = average_score
        report.evaluation = evaluation
        report.daily_analysis = daily_analysis
        report.patterns = patterns
        report.feedback = feedback
        report.status = status
        if s3_key:
            report.s3_key = s3_key
        
        self.db.commit()
        self.db.refresh(report)
        return report
    
    def update_report_status(
        self,
        report_id: int,
        status: str,
        error_message: Optional[str] = None
    ) -> Optional[WeeklyReport]:
        """
        리포트 상태를 업데이트합니다.
        """
        report = self.get_report_by_id(report_id)
        if not report:
            return None
        
        report.status = status
        if error_message:
            report.feedback = [error_message]
        
        self.db.commit()
        self.db.refresh(report)
        return report
    
    def get_latest_report_by_user(self, user_id: str) -> Optional[WeeklyReport]:
        """
        사용자의 가장 최근 리포트를 조회합니다.
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            가장 최근 리포트 또는 None
        """
        stmt = select(WeeklyReport).where(
            WeeklyReport.user_id == user_id
        ).order_by(desc(WeeklyReport.created_at)).limit(1)
        
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    def get_report_by_nickname(self, nickname: str) -> Optional[WeeklyReport]:
        """
        닉네임으로 가장 최근 리포트를 조회합니다.
        
        Args:
            nickname: 닉네임
            
        Returns:
            가장 최근 리포트 또는 None
        """
        stmt = select(WeeklyReport).where(
            WeeklyReport.nickname == nickname
        ).order_by(desc(WeeklyReport.created_at)).limit(1)
        
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    def get_report_by_id(self, report_id: int) -> Optional[WeeklyReport]:
        """
        ID로 리포트를 조회합니다.
        
        Args:
            report_id: 리포트 ID
            
        Returns:
            리포트 또는 None
        """
        stmt = select(WeeklyReport).where(WeeklyReport.id == report_id)
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    def get_reports_by_user(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[WeeklyReport]:
        """
        사용자의 리포트 목록을 조회합니다.
        
        Args:
            user_id: 사용자 ID
            limit: 최대 개수
            
        Returns:
            리포트 목록
        """
        stmt = select(WeeklyReport).where(
            WeeklyReport.user_id == user_id
        ).order_by(desc(WeeklyReport.created_at)).limit(limit)
        
        result = self.db.execute(stmt)
        return list(result.scalars().all())
    
    def report_exists_for_week(
        self,
        user_id: str,
        week_start: date,
        week_end: date
    ) -> bool:
        """
        해당 주에 이미 리포트가 존재하는지 확인합니다.
        
        Args:
            user_id: 사용자 ID
            week_start: 주 시작일
            week_end: 주 종료일
            
        Returns:
            존재 여부
        """
        stmt = select(WeeklyReport).where(
            WeeklyReport.user_id == user_id,
            WeeklyReport.week_start == week_start,
            WeeklyReport.week_end == week_end
        ).limit(1)
        
        result = self.db.execute(stmt)
        return result.scalar_one_or_none() is not None
