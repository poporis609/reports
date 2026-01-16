# app/api/routes/chat.py
"""
Chat API 라우터 - Agent와 대화
"""
import logging
from typing import Optional
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.services.agentcore_service import get_agentcore_service, AgentCoreServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/")
async def chat_with_agent(
    message: str,
    user_id: str = Query(..., description="사용자 ID"),
    session_id: Optional[str] = Query(None, description="세션 ID (대화 유지용)")
):
    """
    Agent와 대화합니다.
    
    - message: 사용자 메시지
    - user_id: 사용자 ID
    - session_id: 세션 ID (같은 세션이면 대화 맥락 유지)
    """
    try:
        agent = get_agentcore_service()
        response = agent.invoke_agent(
            input_text=message,
            user_id=user_id,
            session_id=session_id
        )
        
        return {
            "status": "success",
            "response": response,
            "session_id": session_id
        }
        
    except AgentCoreServiceError as e:
        return {
            "status": "error",
            "error": str(e)
        }


@router.post("/stream")
async def chat_with_agent_stream(
    message: str,
    user_id: str = Query(..., description="사용자 ID"),
    session_id: Optional[str] = Query(None, description="세션 ID")
):
    """
    Agent와 스트리밍으로 대화합니다.
    """
    agent = get_agentcore_service()
    
    def generate():
        try:
            for chunk in agent.invoke_agent_stream(
                input_text=message,
                user_id=user_id,
                session_id=session_id
            ):
                yield chunk
        except AgentCoreServiceError as e:
            yield f"[ERROR] {str(e)}"
    
    return StreamingResponse(
        generate(),
        media_type="text/plain"
    )


@router.post("/report")
async def create_report_via_chat(
    user_id: str = Query(..., description="사용자 ID"),
    start_date: str = Query(..., description="시작일 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="종료일 (YYYY-MM-DD)")
):
    """
    Agent를 통해 리포트를 생성합니다.
    """
    try:
        agent = get_agentcore_service()
        result = agent.create_report_via_agent(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )
        
        return result
        
    except AgentCoreServiceError as e:
        return {
            "status": "error",
            "error": str(e)
        }
