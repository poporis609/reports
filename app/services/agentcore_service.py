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
        
        Args:
            content: 사용자 입력 (자연어)
            user_id: 사용자 ID
            current_date: 현재 날짜 (YYYY-MM-DD)
            request_type: 요청 타입 (summarize, question 등, None이면 자동 판단)
            temperature: summarize용 temperature (0.0 ~ 1.0)
        
        Returns:
            Agent 응답 (type, content, message)
        """
        try:
            # 페이로드 구성 (server.py의 /invocations 형식에 맞춤)
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
            
            # 응답 파싱 - 다양한 응답 형식 지원
            logger.info(f"AgentCore 응답 키: {list(response.keys())}")
            
            if 'body' in response:
                body = response['body']
                if hasattr(body, 'read'):
                    result = json.loads(body.read().decode('utf-8'))
                else:
                    result = json.loads(body) if isinstance(body, str) else body
            elif 'response' in response:
                result = response['response']
                if isinstance(result, str):
                    result = json.loads(result)
            elif 'output' in response:
                result = response['output']
                if isinstance(result, str):
                    result = json.loads(result)
            else:
                # 응답 자체가 결과일 수 있음
                result = response
            
            logger.info(f"AgentCore 응답 완료: type={result.get('type') if isinstance(result, dict) else 'unknown'}")
            return result if isinstance(result, dict) else {"type": "data", "content": str(result), "message": ""}
            
        except Exception as e:
            logger.error(f"AgentCore 호출 실패: {e}")
            raise AgentCoreServiceError(f"Agent 호출 실패: {e}")
    
    def chat(
        self,
        message: str,
        user_id: str,
        current_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Agent와 대화합니다. (일반 대화/질문)
        """
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
        """
        Agent를 통해 주간 리포트를 생성합니다.
        
        Args:
            user_id: 사용자 ID
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)
        
        Returns:
            리포트 생성 결과
        """
        # 자연어 요청 구성
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
    
    def get_report_list_via_agent(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Agent를 통해 리포트 목록을 조회합니다.
        """
        result = self.invoke_agent(
            content="내 리포트 목록 보여줘",
            user_id=user_id
        )
        return {
            "status": "success",
            "type": result.get("type", "report"),
            "content": result.get("content", ""),
            "message": result.get("message", "")
        }
    
    def get_report_detail_via_agent(
        self,
        user_id: str,
        report_id: int
    ) -> Dict[str, Any]:
        """
        Agent를 통해 리포트 상세를 조회합니다.
        """
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
