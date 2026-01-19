# app/services/agentcore_service.py
"""
AWS Bedrock AgentCore 호출 서비스
상대방 레포(Fproject-agent-core)의 Diary Orchestrator Agent를 호출
"""
import boto3
import json
import logging
from typing import Dict, Any, Optional
from functools import lru_cache
from datetime import date

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class AgentCoreServiceError(Exception):
    """AgentCore 서비스 에러"""
    pass


class AgentCoreService:
    """AWS Bedrock AgentCore 호출 서비스"""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = boto3.client(
            "bedrock-agentcore",
            region_name=self.settings.AWS_REGION
        )
        
        # AgentCore Runtime ARN (Diary Orchestrator Agent)
        self.agent_runtime_arn = getattr(
            self.settings, 
            'AGENT_RUNTIME_ARN', 
            "arn:aws:bedrock-agentcore:us-east-1:324547056370:runtime/diary_orchestrator_agent-90S9ctAFht"
        )
    
    def invoke_agent(
        self,
        content: str,
        user_id: Optional[str] = None,
        current_date: Optional[str] = None,
        request_type: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Orchestrator Agent를 호출합니다.
        """
        try:
            # 페이로드 구성
            payload = {"content": content}
            
            if user_id:
                payload["user_id"] = user_id
            if current_date:
                payload["current_date"] = current_date
            if request_type:
                payload["request_type"] = request_type
            if temperature is not None:
                payload["temperature"] = temperature
            
            logger.info(f"AgentCore 호출: user={user_id}, type={request_type}")
            
            response = self.client.invoke_agent_runtime(
                agentRuntimeArn=self.agent_runtime_arn,
                payload=json.dumps(payload).encode('utf-8')
            )
            
            # 응답 파싱
            logger.info(f"AgentCore 응답 키: {list(response.keys())}")
            
            result = None
            
            # 각 키를 순서대로 확인
            for key in ['body', 'response', 'output']:
                if key in response and result is None:
                    data = response[key]
                    if hasattr(data, 'read'):
                        result = json.loads(data.read().decode('utf-8'))
                    elif isinstance(data, bytes):
                        result = json.loads(data.decode('utf-8'))
                    elif isinstance(data, str):
                        try:
                            result = json.loads(data)
                        except json.JSONDecodeError:
                            result = {"type": "data", "content": data, "message": ""}
                    elif isinstance(data, dict):
                        result = data
            
            if result is None:
                result = {"type": "error", "content": "", "message": "응답을 파싱할 수 없습니다"}
            
            logger.info(f"AgentCore 응답 완료: type={result.get('type', 'unknown')}")
            return result
            
        except Exception as e:
            logger.error(f"AgentCore 호출 실패: {e}")
            raise AgentCoreServiceError(f"Agent 호출 실패: {e}")
    
    def chat(
        self,
        message: str,
        user_id: str,
        current_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Agent와 대화합니다."""
        result = self.invoke_agent(
            content=message,
            user_id=user_id,
            current_date=current_date
        )
        return {
            "status": "success",
            "type": result.get("type", "answer"),
            "content": result.get("content", ""),
            "message": result.get("message", "")
        }
    
    def create_report_via_agent(
        self,
        user_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Agent를 통해 주간 리포트를 생성합니다."""
        if start_date and end_date:
            content = f"주간 리포트 생성해줘. 기간: {start_date} ~ {end_date}"
        else:
            content = "이번 주 주간 리포트 생성해줘"
        
        result = self.invoke_agent(
            content=content,
            user_id=user_id,
            current_date=date.today().isoformat()
        )
        
        return {
            "status": "success",
            "type": result.get("type", "report"),
            "content": result.get("content", ""),
            "message": result.get("message", "")
        }
    
    def get_report_list_via_agent(self, user_id: str) -> Dict[str, Any]:
        """Agent를 통해 리포트 목록을 조회합니다."""
        result = self.invoke_agent(content="내 리포트 목록 보여줘", user_id=user_id)
        return {
            "status": "success",
            "type": result.get("type", "report"),
            "content": result.get("content", ""),
            "message": result.get("message", "")
        }
    
    def get_report_detail_via_agent(self, user_id: str, report_id: int) -> Dict[str, Any]:
        """Agent를 통해 리포트 상세를 조회합니다."""
        result = self.invoke_agent(
            content=f"리포트 {report_id}번 상세 내용 보여줘",
            user_id=user_id
        )
        return {
            "status": "success",
            "type": result.get("type", "report"),
            "content": result.get("content", ""),
            "message": result.get("message", "")
        }


@lru_cache()
def get_agentcore_service() -> AgentCoreService:
    """AgentCore 서비스 싱글톤 인스턴스 반환"""
    return AgentCoreService()
