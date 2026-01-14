"""
AWS Secrets Manager에서 애플리케이션 설정을 가져오는 모듈
"""
import json
import logging
import boto3
from functools import lru_cache
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class SecretsManager:
    """AWS Secrets Manager 클라이언트"""
    
    def __init__(self, region_name: str = "us-east-1"):
        self.client = boto3.client("secretsmanager", region_name=region_name)
        self._cache: Dict[str, Any] = {}
    
    def get_secret(self, secret_name: str) -> Optional[Dict[str, Any]]:
        """
        Secrets Manager에서 시크릿을 가져옵니다.
        
        Args:
            secret_name: 시크릿 이름
            
        Returns:
            시크릿 값 (JSON 파싱된 딕셔너리) 또는 None
        """
        # 캐시 확인
        if secret_name in self._cache:
            return self._cache[secret_name]
        
        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            secret_string = response.get("SecretString")
            
            if not secret_string:
                logger.error(f"Secret {secret_name} has no SecretString")
                return None
            
            # JSON 파싱
            try:
                secret_data = json.loads(secret_string)
            except json.JSONDecodeError:
                # JSON이 아니면 문자열 그대로 반환
                secret_data = {"value": secret_string}
            
            # 캐시에 저장
            self._cache[secret_name] = secret_data
            return secret_data
            
        except self.client.exceptions.ResourceNotFoundException:
            logger.error(f"Secret {secret_name} not found")
            return None
        except Exception as e:
            logger.error(f"Failed to get secret {secret_name}: {e}")
            return None
    
    def get_secret_value(self, secret_name: str, key: str, default: Any = None) -> Any:
        """
        Secrets Manager에서 특정 키의 값을 가져옵니다.
        
        Args:
            secret_name: 시크릿 이름
            key: 가져올 키
            default: 기본값
            
        Returns:
            키의 값 또는 기본값
        """
        secret = self.get_secret(secret_name)
        if secret is None:
            return default
        return secret.get(key, default)


@lru_cache()
def get_secrets_manager(region_name: str = "us-east-1") -> SecretsManager:
    """SecretsManager 싱글톤 인스턴스 반환"""
    return SecretsManager(region_name)
