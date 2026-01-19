# app/api/routes/chat.py
"""
Chat API 라우터 - Diary Orchestrator Agent와 대화
"""
import logging
from datetime import date
from typing import Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.services.agentcore_service import get_agentcore_service, AgentCoreServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """채팅 요청"""
    message: str
    user_id: str
    current_date: Optional[str] = None


class ReportRequest(BaseModel):
    """리포트 요청"""
    user_id: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None


@router.post("/")
async def chat_with_agent(request: ChatRequest):
    """
    Orchestrator Agent와 대화합니다.
    
    자연어로 요청하면 orchestrator가 자동으로 적절한 처리를 합니다:
    - 질문 → Question Agent
    - 일기 생성 → Summarize Agent
    - 이미지 생성 → Image Generator Agent
    - 주간 리포트 → Weekly Report Agent
    - 단순 데이터 → 저장
    """
    try:
        agent = get_agentcore_service()
        result = agent.chat(
            message=request.message,
            user_id=request.user_id,
            current_date=request.current_date or date.today().isoformat()
        )
        return result
        
    except AgentCoreServiceError as e:
        logger.error(f"Agent 호출 실패: {e}")
        return {
            "status": "error",
            "type": "error",
            "content": "",
            "message": str(e)
        }


@router.post("/report")
async def create_report_via_chat(request: ReportRequest):
    """
    Agent를 통해 주간 리포트를 생성합니다.
    
    orchestrator → run_weekly_report → reports API 호출
    """
    try:
        agent = get_agentcore_service()
        result = agent.create_report_via_agent(
            user_id=request.user_id,
            start_date=request.start_date,
            end_date=request.end_date
        )
        return result
        
    except AgentCoreServiceError as e:
        logger.error(f"리포트 생성 실패: {e}")
        return {
            "status": "error",
            "type": "error",
            "content": "",
            "message": str(e)
        }


@router.get("/report/list")
async def get_report_list_via_chat(
    user_id: str = Query(..., description="사용자 ID")
):
    """
    Agent를 통해 리포트 목록을 조회합니다.
    """
    try:
        agent = get_agentcore_service()
        result = agent.get_report_list_via_agent(user_id=user_id)
        return result
        
    except AgentCoreServiceError as e:
        logger.error(f"리포트 목록 조회 실패: {e}")
        return {
            "status": "error",
            "type": "error",
            "content": "",
            "message": str(e)
        }


@router.get("/report/{report_id}")
async def get_report_detail_via_chat(
    report_id: int,
    user_id: str = Query(..., description="사용자 ID")
):
    """
    Agent를 통해 리포트 상세를 조회합니다.
    """
    try:
        agent = get_agentcore_service()
        result = agent.get_report_detail_via_agent(
            user_id=user_id,
            report_id=report_id
        )
        return result
        
    except AgentCoreServiceError as e:
        logger.error(f"리포트 상세 조회 실패: {e}")
        return {
            "status": "error",
            "type": "error",
            "content": "",
            "message": str(e)
        }
