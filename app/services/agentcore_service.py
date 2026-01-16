# app/services/agentcore_service.py
"""
AWS Bedrock AgentCore 호출 서비스
"""
import boto3
import json
import logging
from typing import Dict, Any
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
            "bedrock-agentcore",
            region_name=self.settings.AWS_REGION
        )
        
        # AgentCore Runtime ARN
        self.agent_runtime_arn = "arn:aws:bedrock-agentcore:us-east-1:324547056370:runtime/my_agent-2TkF0HCkZE"
    
    def invoke_agent(
        self,
        prompt: str,
        user_id: str = None
    ) -> str:
        """
        Agent를 호출합니다.
        
        Args:
            prompt: 사용자 입력
            user_id: 사용자 ID (optional)
        
        Returns:
            Agent 응답 텍스트
        """
        try:
            # 페이로드 구성
            payload = {"prompt": prompt}
            if user_id:
                payload["user_id"] = user_id
            
            logger.info(f"AgentCore 호출: user={user_id}")
            
            response = self.client.invoke_agent_runtime(
                agentRuntimeArn=self.agent_runtime_arn,
                payload=json.dumps(payload).encode('utf-8')
            )
            
            # 응답 파싱
            result = json.loads(response['body'].read().decode('utf-8'))
            
            logger.info(f"AgentCore 응답 완료")
            return result.get("result", str(result))
            
        except Exception as e:
            logger.error(f"AgentCore 호출 실패: {e}")
            raise AgentCoreServiceError(f"Agent 호출 실패: {e}")
    
    def chat(
        self,
        message: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Agent와 대화합니다.
        """
        response = self.invoke_agent(message, user_id)
        return {
            "status": "success",
            "response": response
        }


@lru_cache()
def get_agentcore_service() -> AgentCoreService:
    """AgentCore 서비스 싱글톤 인스턴스 반환"""
    return AgentCoreService()
