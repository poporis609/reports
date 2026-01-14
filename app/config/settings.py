"""
애플리케이션 설정 모듈
AWS Secrets Manager에서 DB 정보를 가져오고 환경 변수를 관리합니다.
"""
import os
import json
import logging
import boto3
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional

logger = logging.getLogger(__name__)


def get_secret(secret_name: str, region_name: str = "us-east-1") -> dict:
    """AWS Secrets Manager에서 시크릿 값을 가져옵니다."""
    try:
        client = boto3.client("secretsmanager", region_name=region_name)
        response = client.get_secret_value(SecretId=secret_name)
        secret_string = response["SecretString"]
        # JSON 형식인 경우 파싱
        try:
            return json.loads(secret_string)
        except json.JSONDecodeError:
            return {"password": secret_string}
    except Exception as e:
        logger.error(f"Secrets Manager에서 시크릿 가져오기 실패: {e}")
        raise


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # 앱 설정
    APP_NAME: str = "weekly-report-service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # AWS 설정
    AWS_REGION: str = "us-east-1"
    USE_SECRETS_MANAGER: bool = True
    DB_SECRET_NAME: str = "library-api/db-password"
    
    # Bedrock Flow 설정
    BEDROCK_FLOW_ID: str = "BZKT7TJGPT"
    BEDROCK_FLOW_ALIAS_ID: str = "QENFHYZ1KE"
    BEDROCK_TIMEOUT: int = 30
    
    # 데이터베이스 설정 (Secrets Manager 미사용 시)
    DB_HOST: Optional[str] = None
    DB_PORT: int = 5432
    DB_NAME: Optional[str] = None
    DB_USER: Optional[str] = None
    DB_PASSWORD: Optional[str] = None
    
    # Cognito 설정
    COGNITO_USER_POOL_ID: str = "us-east-1_oesTGe9D5"
    COGNITO_CLIENT_ID: str = "6ugujl077j6fmcqgptjmn91b7e"
    
    # SES 설정
    SES_SENDER_EMAIL: str = "noreply@aws11.shop"
    
    # API 설정
    API_BASE_URL: str = "https://api.aws11.shop"
    
    # 캐시된 DB 설정
    _db_config: Optional[dict] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    def _get_db_config(self) -> dict:
        """DB 설정을 가져옵니다 (환경변수 + Secrets Manager에서 비밀번호만)."""
        if self._db_config is not None:
            return self._db_config
        
        # 환경변수에서 기본 DB 정보 가져오기
        password = self.DB_PASSWORD
        
        # Secrets Manager에서 비밀번호만 가져오기
        if self.USE_SECRETS_MANAGER and not password:
            try:
                secret = get_secret(self.DB_SECRET_NAME, self.AWS_REGION)
                # JSON이면 password 키에서, 아니면 전체 문자열이 비밀번호
                if isinstance(secret, dict):
                    password = secret.get("password", secret.get("SecretString", ""))
                else:
                    password = str(secret)
            except Exception as e:
                logger.warning(f"Secrets Manager에서 비밀번호 가져오기 실패: {e}")
        
        self._db_config = {
            "host": self.DB_HOST,
            "port": self.DB_PORT,
            "database": self.DB_NAME,
            "username": self.DB_USER,
            "password": password,
        }
        return self._db_config
    
    def get_database_url(self) -> str:
        """SQLAlchemy 데이터베이스 URL을 반환합니다."""
        config = self._get_db_config()
        return f"postgresql://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"


@lru_cache()
def get_settings() -> Settings:
    """설정 싱글톤 인스턴스를 반환합니다."""
    return Settings()
