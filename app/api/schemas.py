"""
API 스키마 정의
"""
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CreateReportRequest(BaseModel):
    """리포트 생성 요청"""
    start_date: Optional[date] = Field(None, description="분석 시작일 (기본값: 지난 주 월요일)")
    end_date: Optional[date] = Field(None, description="분석 종료일 (기본값: 지난 주 일요일)")


class DailyAnalysisResponse(BaseModel):
    """일별 분석 응답"""
    date: str
    score: float
    sentiment: str
    diary_content: str
    key_themes: List[str]


class PatternResponse(BaseModel):
    """패턴 응답"""
    type: str
    value: str
    correlation: str
    frequency: int
    average_score: float


class CreateReportResponse(BaseModel):
    """리포트 생성 응답"""
    report_id: int
    user_id: str
    nickname: str
    week_period: Dict[str, str]
    average_score: float
    evaluation: str
    daily_analysis: List[DailyAnalysisResponse]
    patterns: List[PatternResponse]
    feedback: List[str]
    has_partial_data: bool
    created_at: str
    s3_key: Optional[str] = None


class ReportSummaryResponse(BaseModel):
    """리포트 요약 응답"""
    report_id: int
    nickname: str
    created_at: str
    summary: Dict[str, Any]


class ErrorResponse(BaseModel):
    """에러 응답"""
    error: Dict[str, Any]


class HealthResponse(BaseModel):
    """헬스 체크 응답"""
    status: str
    service: str
