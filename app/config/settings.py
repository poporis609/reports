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
        # 개발 환경에서는 에러를 발생시키지 않고 빈 딕셔너리 반환
        return {}


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
    APP_CONFIG_SECRET_NAME: str = "weekly-report/app-config"
    
    # Bedrock Flow 설정 (환경 변수 또는 Secrets Manager에서)
    BEDROCK_FLOW_ID: Optional[str] = None
    BEDROCK_FLOW_ALIAS_ID: Optional[str] = None
    BEDROCK_TIMEOUT: int = 30
    
    # 데이터베이스 설정 (Secrets Manager 미사용 시)
    DB_HOST: Optional[str] = None
    DB_PORT: int = 5432
    DB_NAME: Optional[str] = None
    DB_USER: Optional[str] = None
    DB_PASSWORD: Optional[str] = None
    
    # Cognito 설정 (환경 변수 또는 Secrets Manager에서)
    COGNITO_USER_POOL_ID: Optional[str] = None
    COGNITO_CLIENT_ID: Optional[str] = None
    
    # SES 설정
    SES_SENDER_EMAIL: str = "noreply@aws11.shop"
    
    # API 설정
    API_BASE_URL: str = "https://api.aws11.shop"
    
    # 캐시된 설정
    _db_config: Optional[dict] = None
    _app_config: Optional[dict] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    def _get_app_config(self) -> dict:
        """애플리케이션 설정을 Secrets Manager에서 가져옵니다."""
        if self._app_config is not None:
            return self._app_config
        
        config = {}
        
        # Secrets Manager에서 가져오기 시도
        if self.USE_SECRETS_MANAGER:
            try:
                secret = get_secret(self.APP_CONFIG_SECRET_NAME, self.AWS_REGION)
                config = secret
                logger.info(f"Loaded app config from Secrets Manager: {self.APP_CONFIG_SECRET_NAME}")
            except Exception as e:
                logger.warning(f"Failed to load app config from Secrets Manager: {e}")
        
        # 환경 변수로 오버라이드 (환경 변수가 우선)
        if self.BEDROCK_FLOW_ID:
            config["BEDROCK_FLOW_ID"] = self.BEDROCK_FLOW_ID
        if self.BEDROCK_FLOW_ALIAS_ID:
            config["BEDROCK_FLOW_ALIAS_ID"] = self.BEDROCK_FLOW_ALIAS_ID
        if self.COGNITO_USER_POOL_ID:
            config["COGNITO_USER_POOL_ID"] = self.COGNITO_USER_POOL_ID
        if self.COGNITO_CLIENT_ID:
            config["COGNITO_CLIENT_ID"] = self.COGNITO_CLIENT_ID
        
        self._app_config = config
        return config
    
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
    
    def get_bedrock_flow_id(self) -> str:
        """Bedrock Flow ID를 반환합니다."""
        config = self._get_app_config()
        return config.get("BEDROCK_FLOW_ID", self.BEDROCK_FLOW_ID or "")
    
    def get_bedrock_flow_alias_id(self) -> str:
        """Bedrock Flow Alias ID를 반환합니다."""
        config = self._get_app_config()
        return config.get("BEDROCK_FLOW_ALIAS_ID", self.BEDROCK_FLOW_ALIAS_ID or "")
    
    def get_cognito_user_pool_id(self) -> str:
        """Cognito User Pool ID를 반환합니다."""
        config = self._get_app_config()
        return config.get("COGNITO_USER_POOL_ID", self.COGNITO_USER_POOL_ID or "")
    
    def get_cognito_client_id(self) -> str:
        """Cognito Client ID를 반환합니다."""
        config = self._get_app_config()
        return config.get("COGNITO_CLIENT_ID", self.COGNITO_CLIENT_ID or "")


@lru_cache()
def get_settings() -> Settings:
    """설정 싱글톤 인스턴스를 반환합니다."""
    return Settings()
