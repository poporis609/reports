# app/api/routes/agent_report.py
"""
Weekly Report Agent Endpoint
POST /agent/report

직접 리포트 생성/조회/목록 처리 (AgentCore 없이)
"""
from fastapi import APIRouter, Request, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import json
import logging
from datetime import date, datetime

from app.config.database import get_db, SessionLocal
from app.services.strands_service import get_strands_service
from app.services.report_service import ReportAnalysisService
from app.services.email_service import EmailService
from app.services.s3_service import S3Service, S3ServiceError
from app.repositories import HistoryRepository, UserRepository, ReportRepository

logger = logging.getLogger(__name__)
router = APIRouter()


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
        
        # 감정 분석
        analysis = strands.analyze_sentiment(entry_dicts, nickname)
        
        # 리포트 생성
        report_result = report_service.generate_report(
            user_id=user_id,
            nickname=nickname,
            week_start=week_start,
            week_end=week_end,
            entries=entry_dicts,
            analysis=analysis
        )
        
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
        try:
            report_repo = ReportRepository(db)
            report_repo.update_report_status(report_id, "failed", str(e))
        except:
            pass
    finally:
        db.close()


def _parse_request_intent(content: str) -> str:
    """요청 내용에서 의도 파악"""
    content_lower = content.lower()
    
    if any(keyword in content_lower for keyword in ["생성", "만들어", "작성"]):
        return "create"
    elif any(keyword in content_lower for keyword in ["목록", "리스트", "보여줘"]):
        return "list"
    elif any(keyword in content_lower for keyword in ["상세", "조회", "보기"]):
        return "detail"
    else:
        return "create"  # 기본값


@router.post("")
async def process_report_request(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    주간 리포트 처리 엔드포인트
    
    요청 파라미터:
    - content (필수): 사용자 요청 (자연어)
    - user_id (선택): 사용자 ID
    - start_date (선택): 시작일 (YYYY-MM-DD)
    - end_date (선택): 종료일 (YYYY-MM-DD)
    - report_id (선택): 리포트 ID (조회 시)
    """
    try:
        body = await request.json()
        
        logger.info(f"[Agent/Report] Request: {json.dumps(body, ensure_ascii=False)[:200]}...")
        
        content = body.get('content')
        user_id = body.get('user_id')
        start_date_str = body.get('start_date')
        end_date_str = body.get('end_date')
        report_id = body.get('report_id')
        
        if not content:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "요청 내용(content)이 필요합니다."
                }
            )
        
        # 의도 파악
        intent = _parse_request_intent(content)
        
        # 리포지토리 초기화
        report_repo = ReportRepository(db)
        user_repo = UserRepository(db)
        history_repo = HistoryRepository(db)
        report_service = ReportAnalysisService()
        
        # === 리포트 목록 조회 ===
        if intent == "list":
            if not user_id:
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "error": "user_id가 필요합니다."}
                )
            
            reports = report_repo.get_reports_by_user(user_id, limit=10)
            return JSONResponse(content={
                "success": True,
                "type": "report_list",
                "data": [r.to_dict() for r in reports],
                "message": f"{len(reports)}개의 리포트를 찾았습니다."
            })
        
        # === 리포트 상세 조회 ===
        if intent == "detail":
            if not report_id:
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "error": "report_id가 필요합니다."}
                )
            
            report = report_repo.get_report_by_id(int(report_id))
            if not report:
                return JSONResponse(
                    status_code=404,
                    content={"success": False, "error": "리포트를 찾을 수 없습니다."}
                )
            
            return JSONResponse(content={
                "success": True,
                "type": "report_detail",
                "data": report.to_dict(),
                "message": "리포트 조회 완료"
            })
        
        # === 리포트 생성 ===
        if not user_id:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "user_id가 필요합니다."}
            )
        
        # 사용자 정보 조회
        user = user_repo.get_user_by_id(user_id)
        if not user:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "사용자를 찾을 수 없습니다."}
            )
        
        nickname = user.nickname or user.email
        email = user.email
        
        # 분석 기간 결정
        if start_date_str and end_date_str:
            week_start = date.fromisoformat(start_date_str)
            week_end = date.fromisoformat(end_date_str)
        else:
            week_start, week_end = report_service.get_previous_week_range()
        
        # 일기 항목 조회
        entries = history_repo.get_entries_by_user_and_period(user_id, week_start, week_end)
        
        if not entries:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": f"분석 기간({week_start} ~ {week_end})에 일기가 없습니다."
                }
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
        
        # "처리 중" 상태로 리포트 생성
        saved_report = report_repo.save_report(
            user_id=user_id,
            nickname=nickname,
            week_start=week_start,
            week_end=week_end,
            average_score=0.0,
            evaluation="positive",
            daily_analysis=[],
            patterns=[],
            feedback=["리포트를 생성하고 있습니다."],
            s3_key=None,
            status="processing"
        )
        
        # 백그라운드에서 리포트 생성
        background_tasks.add_task(
            _process_report_background,
            saved_report.id,
            user_id,
            nickname,
            email,
            week_start,
            week_end,
            entry_dicts,
        )
        
        return JSONResponse(content={
            "success": True,
            "type": "report_create",
            "data": {
                "report_id": saved_report.id,
                "status": "processing",
                "week_period": {
                    "start": week_start.isoformat(),
                    "end": week_end.isoformat()
                }
            },
            "message": "리포트 생성이 시작되었습니다. 완료까지 1-2분 정도 소요됩니다."
        })
        
    except Exception as e:
        logger.error(f"[Agent/Report] Error: {e}")
        import traceback
        traceback.print_exc()
        
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"리포트 처리 중 오류가 발생했습니다: {str(e)}"
            }
        )
