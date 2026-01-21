"""
Application Configuration
Fproject-agent 패턴에 맞춘 설정 모듈
"""
from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "weekly-report-service"
    VERSION: str = "1.0.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    
    # AWS 설정
    AWS_REGION: str = "us-east-1"
    USE_SECRETS_MANAGER: bool = True
    DB_SECRET_NAME: str = "library-api/db-password"
    APP_CONFIG_SECRET_NAME: str = "weekly-report/app-config"
    
    # Bedrock Flow 설정
    BEDROCK_FLOW_ID: Optional[str] = None
    BEDROCK_FLOW_ALIAS_ID: Optional[str] = None
    BEDROCK_TIMEOUT: int = 300
    
    # 데이터베이스 설정
    DB_HOST: Optional[str] = None
    DB_PORT: int = 5432
    DB_NAME: Optional[str] = None
    DB_USER: Optional[str] = None
    DB_PASSWORD: Optional[str] = None
    
    # Cognito 설정
    COGNITO_USER_POOL_ID: Optional[str] = None
    COGNITO_CLIENT_ID: Optional[str] = None
    
    # SES 설정
    SES_SENDER_EMAIL: str = "noreply@aws11.shop"
    
    # API 설정
    API_BASE_URL: str = "https://api.aws11.shop"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """설정 싱글톤 인스턴스를 반환합니다."""
    return Settings()


settings = get_settings()
