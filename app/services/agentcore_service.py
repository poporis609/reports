# app/services/agentcore_service.py
"""
AWS Bedrock AgentCore 호출 서비스
배포된 Agent를 호출하는 클라이언트
"""
import boto3
import logging
import uuid
from typing import Dict, Any, Generator
from functools import lru_cache

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
            "bedrock-agent-runtime",
            region_name=self.settings.AWS_REGION
        )
        
        # Agent 설정 (배포 후 설정 필요)
        self.agent_id = self.settings.get_bedrock_flow_id()  # 또는 별도 설정
        self.agent_alias_id = self.settings.get_bedrock_flow_alias_id()  # 또는 별도 설정
    
    def invoke_agent(
        self,
        input_text: str,
        user_id: str = None,
        session_id: str = None
    ) -> str:
        """
        Agent를 호출합니다.
        
        Args:
            input_text: 사용자 입력
            user_id: 사용자 ID (optional)
            session_id: 세션 ID (optional, 없으면 자동 생성)
        
        Returns:
            Agent 응답 텍스트
        """
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # user_id가 있으면 프롬프트에 추가
        if user_id:
            prompt = f"[사용자 ID: {user_id}]\n\n{input_text}"
        else:
            prompt = input_text
        
        try:
            logger.info(f"AgentCore 호출: session={session_id}")
            
            response = self.client.invoke_agent(
                agentId=self.agent_id,
                agentAliasId=self.agent_alias_id,
                sessionId=session_id,
                inputText=prompt
            )
            
            # 응답 스트림 처리
            result = ""
            for event in response.get("completion", []):
                if "chunk" in event:
                    chunk = event["chunk"]
                    if "bytes" in chunk:
                        result += chunk["bytes"].decode("utf-8")
            
            logger.info(f"AgentCore 응답 완료: session={session_id}")
            return result
            
        except Exception as e:
            logger.error(f"AgentCore 호출 실패: {e}")
            raise AgentCoreServiceError(f"Agent 호출 실패: {e}")
    
    def invoke_agent_stream(
        self,
        input_text: str,
        user_id: str = None,
        session_id: str = None
    ) -> Generator[str, None, None]:
        """
        Agent를 스트리밍으로 호출합니다.
        
        Args:
            input_text: 사용자 입력
            user_id: 사용자 ID (optional)
            session_id: 세션 ID (optional)
        
        Yields:
            응답 청크
        """
        if not session_id:
            session_id = str(uuid.uuid4())
        
        if user_id:
            prompt = f"[사용자 ID: {user_id}]\n\n{input_text}"
        else:
            prompt = input_text
        
        try:
            response = self.client.invoke_agent(
                agentId=self.agent_id,
                agentAliasId=self.agent_alias_id,
                sessionId=session_id,
                inputText=prompt
            )
            
            for event in response.get("completion", []):
                if "chunk" in event:
                    chunk = event["chunk"]
                    if "bytes" in chunk:
                        yield chunk["bytes"].decode("utf-8")
                        
        except Exception as e:
            logger.error(f"AgentCore 스트리밍 실패: {e}")
            raise AgentCoreServiceError(f"Agent 스트리밍 실패: {e}")
    
    def create_report_via_agent(
        self,
        user_id: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        Agent를 통해 리포트를 생성합니다.
        
        Args:
            user_id: 사용자 ID
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)
        
        Returns:
            생성된 리포트 정보
        """
        prompt = f"""
{start_date}부터 {end_date}까지 주간 감정 분석 리포트를 생성해주세요.

1. 먼저 사용자 정보를 확인하세요
2. 해당 기간의 일기를 가져오세요
3. 각 일기를 분석하여 감정 점수와 패턴을 파악하세요
4. 분석 결과를 저장하세요
5. 최종 리포트 요약을 반환하세요
"""
        
        response = self.invoke_agent(
            input_text=prompt,
            user_id=user_id
        )
        
        return {
            "status": "completed",
            "response": response
        }


@lru_cache()
def get_agentcore_service() -> AgentCoreService:
    """AgentCore 서비스 싱글톤 인스턴스 반환"""
    return AgentCoreService()
