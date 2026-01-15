"""
리포트 API 라우터 - 주간 감정 분석 리포트 생성 및 조회
"""
import logging
from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.api.schemas import (
    CreateReportRequest,
    CreateReportResponse,
    ReportSummaryResponse,
    DailyAnalysisResponse,
    PatternResponse,
)
from app.services.cognito_service import get_cognito_service, CognitoService
from app.services.bedrock_service import get_bedrock_service, BedrockService, BedrockServiceError, BedrockTimeoutError
from app.services.report_service import ReportAnalysisService
from app.services.email_service import get_email_service, EmailService
from app.services.s3_service import get_s3_service, S3Service, S3ServiceError
from app.repositories import HistoryRepository, UserRepository, ReportRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/report", tags=["report"])


@router.get("/health")
async def health_check():
    """리포트 서비스 헬스 체크"""
    return {"status": "healthy", "service": "weekly-report"}


def _send_email_background(
    email_service: EmailService,
    recipient_email: str,
    report_result
):
    """백그라운드에서 이메일 발송"""
    try:
        email_service.send_report_notification(recipient_email, report_result)
    except Exception as e:
        logger.error(f"백그라운드 이메일 발송 실패: {e}")


@router.post("/create", response_model=CreateReportResponse)
async def create_report(
    request: CreateReportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    bedrock: BedrockService = Depends(get_bedrock_service),
    email_service: EmailService = Depends(get_email_service),
    s3_service: S3Service = Depends(get_s3_service),
    cognito: CognitoService = Depends(get_cognito_service),
):
    """
    주간 리포트를 생성합니다.
    
    - user_id를 받아서 해당 사용자의 일기를 분석하여 주간 리포트를 생성합니다.
    - 분석 기간을 지정하지 않으면 지난 주(월~일)를 분석합니다.
    - 리포트는 S3에 텍스트 파일로 저장됩니다.
    - 리포트 생성 완료 시 이메일 알림을 발송합니다.
    """
    # user_id 필수 체크
    if not request.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id는 필수입니다"
        )
    
    # 리포지토리 초기화
    history_repo = HistoryRepository(db)
    user_repo = UserRepository(db)
    report_repo = ReportRepository(db)
    report_service = ReportAnalysisService()
    
    # 사용자 정보 조회
    user = user_repo.get_user_by_id(request.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다"
        )
    
    nickname = user.nickname or user.email
    email = user.email
    
    # 분석 기간 결정
    if request.start_date and request.end_date:
        week_start = request.start_date
        week_end = request.end_date
    else:
        week_start, week_end = report_service.get_previous_week_range()
    
    # 날짜 유효성 검사
    if week_start > week_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="시작일이 종료일보다 늦을 수 없습니다"
        )
    
    # 일기 항목 조회
    entries = history_repo.get_entries_by_user_and_period(
        request.user_id, week_start, week_end
    )
    
    if not entries:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"분석 기간({week_start} ~ {week_end})에 일기가 없습니다"
        )
    
    # 일기 데이터 변환
    entry_dicts = [
        {
            "id": e.id,
            "content": e.content,
            "record_date": e.record_date,
            "tags": e.tags or []
        }
        for e in entries
    ]
    
    try:
        # Bedrock 감정 분석
        analysis = bedrock.analyze_sentiment(entry_dicts, nickname)
        
        # 리포트 생성
        report_result = report_service.generate_report(
            user_id=request.user_id,
            nickname=nickname,
            week_start=week_start,
            week_end=week_end,
            entries=entry_dicts,
            analysis=analysis
        )
        
        # 현재 시간
        created_at = datetime.utcnow()
        
        # S3에 리포트 저장
        report_data_for_s3 = {
            "nickname": report_result.nickname,
            "week_start": report_result.week_start.isoformat(),
            "week_end": report_result.week_end.isoformat(),
            "average_score": report_result.average_score,
            "evaluation": report_result.evaluation,
            "daily_analysis": [d.to_dict() for d in report_result.daily_analysis],
            "patterns": [p.to_dict() for p in report_result.patterns],
            "feedback": report_result.feedback,
            "created_at": created_at.isoformat()
        }
        
        try:
            s3_key = s3_service.upload_report(
                user_id=request.user_id,
                report_data=report_data_for_s3,
                created_at=created_at
            )
        except S3ServiceError as e:
            logger.warning(f"S3 업로드 실패, DB에만 저장: {e}")
            s3_key = None
        
        # DB에 저장
        saved_report = report_repo.save_report(
            user_id=report_result.user_id,
            nickname=report_result.nickname,
            week_start=report_result.week_start,
            week_end=report_result.week_end,
            average_score=report_result.average_score,
            evaluation=report_result.evaluation,
            daily_analysis=[d.to_dict() for d in report_result.daily_analysis],
            patterns=[p.to_dict() for p in report_result.patterns],
            feedback=report_result.feedback,
            s3_key=s3_key
        )
        
        # 백그라운드에서 이메일 발송
        background_tasks.add_task(
            _send_email_background,
            email_service,
            email,
            report_result
        )
        
        # 응답 생성
        return CreateReportResponse(
            report_id=saved_report.id,
            user_id=saved_report.user_id,
            nickname=saved_report.nickname,
            week_period={
                "start": saved_report.week_start.isoformat(),
                "end": saved_report.week_end.isoformat()
            },
            average_score=float(saved_report.average_score),
            evaluation=saved_report.evaluation,
            daily_analysis=[
                DailyAnalysisResponse(**d) for d in saved_report.daily_analysis
            ],
            patterns=[
                PatternResponse(**p) for p in saved_report.patterns
            ],
            feedback=saved_report.feedback,
            has_partial_data=report_result.has_partial_data,
            created_at=saved_report.created_at.isoformat(),
            s3_key=saved_report.s3_key
        )
        
    except BedrockTimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI 분석 요청 시간이 초과되었습니다. 잠시 후 다시 시도해주세요."
        )
    except BedrockServiceError as e:
        logger.error(f"Bedrock 서비스 에러: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI 분석 서비스를 일시적으로 사용할 수 없습니다",
            headers={"Retry-After": "60"}
        )
    except Exception as e:
        logger.error(f"리포트 생성 에러: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="리포트 생성 중 오류가 발생했습니다"
        )


@router.get("/search/{nickname}", response_model=ReportSummaryResponse)
async def get_report_by_nickname(
    nickname: str,
    db: Session = Depends(get_db),
    cognito: CognitoService = Depends(get_cognito_service),
):
    """
    닉네임으로 가장 최근 리포트 요약을 조회합니다.
    
    - 닉네임에 해당하는 사용자의 가장 최근 주간 리포트를 반환합니다.
    """
    # 닉네임으로 사용자 조회 (Cognito)
    user_info = cognito.get_user_by_nickname(nickname)
    
    if not user_info:
        # DB에서도 조회 시도
        user_repo = UserRepository(db)
        db_user = user_repo.get_user_by_nickname(nickname)
        
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"닉네임 '{nickname}'에 해당하는 사용자를 찾을 수 없습니다"
            )
    
    # 리포트 조회
    report_repo = ReportRepository(db)
    report = report_repo.get_report_by_nickname(nickname)
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"'{nickname}'님의 주간 리포트가 없습니다"
        )
    
    # 요약 생성
    diary_contents = [
        d.get("diary_content", "") for d in report.daily_analysis
    ]
    
    return ReportSummaryResponse(
        report_id=report.id,
        nickname=report.nickname,
        created_at=report.created_at.isoformat(),
        summary={
            "diary_content": diary_contents,
            "current_date": datetime.now().isoformat(),
            "author_nickname": report.nickname,
            "average_score": float(report.average_score),
            "evaluation": report.evaluation,
            "week_period": {
                "start": report.week_start.isoformat(),
                "end": report.week_end.isoformat()
            }
        }
    )


@router.get("/{report_id}")
async def get_report_by_id(
    report_id: int,
    user_id: str = Query(..., description="사용자 ID"),
    db: Session = Depends(get_db),
):
    """
    리포트 ID로 상세 리포트를 조회합니다.
    
    - user_id를 제공하여 본인의 리포트만 조회할 수 있습니다.
    """
    report_repo = ReportRepository(db)
    report = report_repo.get_report_by_id(report_id)
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="리포트를 찾을 수 없습니다"
        )
    
    # 본인 리포트인지 확인
    if report.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="다른 사용자의 리포트에 접근할 수 없습니다"
        )
    
    return report.to_dict()


@router.get("/")
async def get_my_reports(
    user_id: str = Query(..., description="사용자 ID"),
    limit: int = Query(10, description="조회할 개수"),
    db: Session = Depends(get_db),
):
    """
    내 리포트 목록을 조회합니다.
    """
    report_repo = ReportRepository(db)
    reports = report_repo.get_reports_by_user(user_id, limit)
    
    return {
        "reports": [r.to_dict() for r in reports],
        "total": len(reports)
    }


@router.get("/{report_id}/file")
async def get_report_file(
    report_id: int,
    user_id: str = Query(..., description="사용자 ID"),
    db: Session = Depends(get_db),
    s3_service: S3Service = Depends(get_s3_service),
):
    """
    리포트 파일(S3)을 조회합니다.
    
    - user_id를 제공하여 본인의 리포트 파일만 조회할 수 있습니다.
    - S3에 저장된 텍스트 파일 내용을 반환합니다.
    """
    report_repo = ReportRepository(db)
    report = report_repo.get_report_by_id(report_id)
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="리포트를 찾을 수 없습니다"
        )
    
    # 본인 리포트인지 확인
    if report.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="다른 사용자의 리포트에 접근할 수 없습니다"
        )
    
    # S3 키 확인
    if not report.s3_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="리포트 파일이 존재하지 않습니다"
        )
    
    try:
        content = s3_service.get_report(report.s3_key)
        return {
            "report_id": report_id,
            "s3_key": report.s3_key,
            "content": content
        }
    except S3ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/{report_id}/download-url")
async def get_report_download_url(
    report_id: int,
    user_id: str = Query(..., description="사용자 ID"),
    db: Session = Depends(get_db),
    s3_service: S3Service = Depends(get_s3_service),
):
    """
    리포트 파일 다운로드 URL을 생성합니다.
    
    - user_id를 제공하여 본인의 리포트만 다운로드할 수 있습니다.
    - 1시간 동안 유효한 presigned URL을 반환합니다.
    """
    report_repo = ReportRepository(db)
    report = report_repo.get_report_by_id(report_id)
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="리포트를 찾을 수 없습니다"
        )
    
    # 본인 리포트인지 확인
    if report.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="다른 사용자의 리포트에 접근할 수 없습니다"
        )
    
    # S3 키 확인
    if not report.s3_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="리포트 파일이 존재하지 않습니다"
        )
    
    try:
        download_url = s3_service.generate_presigned_url(report.s3_key)
        return {
            "report_id": report_id,
            "download_url": download_url,
            "expires_in": 3600
        }
    except S3ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
