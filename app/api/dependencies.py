"""
FastAPI 의존성 - 인증 및 공통 의존성
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from app.config.database import get_db
from app.services.cognito_service import CognitoService, UserInfo, get_cognito_service
from app.repositories import UserRepository


# HTTP Bearer 토큰 스키마
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    cognito: CognitoService = Depends(get_cognito_service),
) -> UserInfo:
    """
    현재 인증된 사용자를 가져옵니다.
    
    Args:
        credentials: HTTP Authorization 헤더의 Bearer 토큰
        cognito: Cognito 서비스
        
    Returns:
        인증된 사용자 정보
        
    Raises:
        HTTPException: 인증 실패 시 401 에러
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 토큰이 필요합니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    # 토큰으로 사용자 정보 가져오기
    user_info = cognito.get_user_info(token)
    
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 토큰입니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_info


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    cognito: CognitoService = Depends(get_cognito_service),
) -> Optional[UserInfo]:
    """
    현재 인증된 사용자를 가져옵니다 (선택적).
    인증되지 않은 경우 None을 반환합니다.
    
    Args:
        credentials: HTTP Authorization 헤더의 Bearer 토큰
        cognito: Cognito 서비스
        
    Returns:
        인증된 사용자 정보 또는 None
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    user_info = cognito.get_user_info(token)
    
    return user_info


def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    """UserRepository 의존성"""
    return UserRepository(db)
