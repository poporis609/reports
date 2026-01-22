"""
리포트 API 라우터 - 주간 감정 분석 리포트 생성 및 조회
user_id 파라미터로 인증 없이 접근 가능
"""
import logging
from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.orm import Session

from app.config.database import get_db, SessionLocal
from app.api.schemas import (
    CreateReportRequest,
    CreateReportResponse,
    ReportSummaryResponse,
    DailyAnalysisResponse,
    PatternResponse,
)
from app.services.cognito_service import get_cognito_service, CognitoService
from app.services.strands_service import get_strands_service, StrandsAgentService, StrandsServiceError
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


def _process_report_background(
    report_id: int,
    user_id: str,
    nickname: str,
    email: str,
    week_start: date,
    week_end: date,
    entry_dicts: list,
):
    """백그라운드에서 리포트 생성 처리"""
    db = SessionLocal()
    try:
        strands = get_strands_service()
        report_service = ReportAnalysisService()
        report_repo = ReportRepository(db)
        s3_service = S3Service()
        email_service = EmailService()
        
        logger.info(f"백그라운드 리포트 생성 시작: report_id={report_id}")
        
        # Fproject-agent API를 통한 감정 분석
        analysis = strands.analyze_sentiment(
            entries=entry_dicts,
            nickname=nickname,
            user_id=user_id,
            start_date=week_start.isoformat(),
            end_date=week_end.isoformat()
        )
        
        # 리포트 생성
        report_result = report_service.generate_report(
            user_id=user_id,
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
        
        s3_key = None
        try:
            s3_key = s3_service.upload_report(
                user_id=user_id,
                report_data=report_data_for_s3,
                created_at=created_at
            )
        except S3ServiceError as e:
            logger.warning(f"S3 업로드 실패: {e}")
        
        # DB 업데이트
        report_repo.update_report(
            report_id=report_id,
            average_score=report_result.average_score,
            evaluation=report_result.evaluation,
            daily_analysis=[d.to_dict() for d in report_result.daily_analysis],
            patterns=[p.to_dict() for p in report_result.patterns],
            feedback=report_result.feedback,
            s3_key=s3_key,
            status="completed"
        )
        
        # 이메일 발송
        try:
            email_service.send_report_notification(email, report_result)
        except Exception as e:
            logger.error(f"이메일 발송 실패: {e}")
        
        logger.info(f"백그라운드 리포트 생성 완료: report_id={report_id}")
        
    except Exception as e:
        logger.error(f"백그라운드 리포트 생성 실패: report_id={report_id}, error={e}")
        # 실패 상태로 업데이트
        try:
            report_repo = ReportRepository(db)
            report_repo.update_report_status(report_id, "failed", str(e))
        except:
            pass
    finally:
        db.close()


@router.post("/create")
async def create_report(
    request: CreateReportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    주간 리포트 생성을 요청합니다.
    
    - 리포트 생성은 백그라운드에서 처리됩니다.
    - 즉시 report_id와 status="processing"을 반환합니다.
    - GET /report/{report_id}로 완료 여부를 확인할 수 있습니다.
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
    
    # "처리 중" 상태로 리포트 생성 (evaluation은 CHECK 제약조건 때문에 'positive' 사용)
    saved_report = report_repo.save_report(
        user_id=request.user_id,
        nickname=nickname,
        week_start=week_start,
        week_end=week_end,
        average_score=0.0,
        evaluation="positive",
        daily_analysis=[],
        patterns=[],
        feedback=["리포트를 생성하고 있습니다. 잠시만 기다려주세요."],
        s3_key=None,
        status="processing"
    )
    
    # 백그라운드에서 리포트 생성
    background_tasks.add_task(
        _process_report_background,
        saved_report.id,
        request.user_id,
        nickname,
        email,
        week_start,
        week_end,
        entry_dicts,
    )
    
    # 즉시 응답 반환
    return {
        "report_id": saved_report.id,
        "user_id": saved_report.user_id,
        "nickname": saved_report.nickname,
        "status": "processing",
        "message": "리포트 생성이 시작되었습니다. 완료까지 1-2분 정도 소요됩니다.",
        "week_period": {
            "start": week_start.isoformat(),
            "end": week_end.isoformat()
        },
        "created_at": saved_report.created_at.isoformat()
    }



@router.get("/status/{report_id}")
async def get_report_status(
    report_id: int,
    user_id: str = Query(..., description="사용자 ID"),
    db: Session = Depends(get_db),
):
    """
    리포트 생성 상태를 조회합니다.
    
    - status: processing, completed, failed
    """
    report_repo = ReportRepository(db)
    report = report_repo.get_report_by_id(report_id)
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="리포트를 찾을 수 없습니다"
        )
    
    if report.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="다른 사용자의 리포트에 접근할 수 없습니다"
        )
    
    return {
        "report_id": report.id,
        "status": getattr(report, 'status', 'completed'),
        "created_at": report.created_at.isoformat()
    }


@router.get("/search/{nickname}", response_model=ReportSummaryResponse)
async def get_report_by_nickname(
    nickname: str,
    db: Session = Depends(get_db),
    cognito: CognitoService = Depends(get_cognito_service),
):
    """
    닉네임으로 가장 최근 리포트 요약을 조회합니다.
    """
    user_info = cognito.get_user_by_nickname(nickname)
    
    if not user_info:
        user_repo = UserRepository(db)
        db_user = user_repo.get_user_by_nickname(nickname)
        
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"닉네임 '{nickname}'에 해당하는 사용자를 찾을 수 없습니다"
            )
    
    report_repo = ReportRepository(db)
    report = report_repo.get_report_by_nickname(nickname)
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"'{nickname}'님의 주간 리포트가 없습니다"
        )
    
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
    """리포트 ID로 상세 리포트를 조회합니다."""
    report_repo = ReportRepository(db)
    report = report_repo.get_report_by_id(report_id)
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="리포트를 찾을 수 없습니다"
        )
    
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
    """내 리포트 목록을 조회합니다."""
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
    """리포트 파일(S3)을 조회합니다."""
    report_repo = ReportRepository(db)
    report = report_repo.get_report_by_id(report_id)
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="리포트를 찾을 수 없습니다"
        )
    
    if report.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="다른 사용자의 리포트에 접근할 수 없습니다"
        )
    
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
    """리포트 파일 다운로드 URL을 생성합니다."""
    report_repo = ReportRepository(db)
    report = report_repo.get_report_by_id(report_id)
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="리포트를 찾을 수 없습니다"
        )
    
    if report.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="다른 사용자의 리포트에 접근할 수 없습니다"
        )
    
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
