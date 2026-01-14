"""
Cognito 서비스 - 사용자 인증 및 정보 조회
"""
import boto3
import httpx
from jose import jwt, JWTError
from typing import Optional, Dict, Any
from dataclasses import dataclass
from functools import lru_cache

from app.config.settings import get_settings


@dataclass
class UserInfo:
    """사용자 정보"""
    user_id: str       # Cognito sub
    email: str
    nickname: str      # preferred_username


class CognitoService:
    """Cognito 인증 및 사용자 관리 서비스"""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = boto3.client(
            "cognito-idp",
            region_name=self.settings.AWS_REGION
        )
        self.user_pool_id = self.settings.get_cognito_user_pool_id()
        self.client_id = self.settings.get_cognito_client_id()
        self._jwks = None
    
    @property
    def jwks_url(self) -> str:
        """JWKS URL 반환"""
        return f"https://cognito-idp.{self.settings.AWS_REGION}.amazonaws.com/{self.user_pool_id}/.well-known/jwks.json"
    
    @property
    def issuer(self) -> str:
        """토큰 발급자 URL 반환"""
        return f"https://cognito-idp.{self.settings.AWS_REGION}.amazonaws.com/{self.user_pool_id}"
    
    async def _get_jwks(self) -> Dict[str, Any]:
        """JWKS 키 가져오기 (캐싱)"""
        if self._jwks is None:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.jwks_url)
                self._jwks = response.json()
        return self._jwks
    
    def _get_jwks_sync(self) -> Dict[str, Any]:
        """JWKS 키 가져오기 (동기)"""
        if self._jwks is None:
            with httpx.Client() as client:
                response = client.get(self.jwks_url)
                self._jwks = response.json()
        return self._jwks
    
    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        JWT 토큰을 검증합니다.
        
        Args:
            token: JWT 액세스 토큰
            
        Returns:
            검증된 토큰 페이로드 또는 None
        """
        try:
            # 토큰 헤더에서 kid 추출
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            
            if not kid:
                return None
            
            # JWKS에서 해당 키 찾기
            jwks = await self._get_jwks()
            key = None
            for k in jwks.get("keys", []):
                if k.get("kid") == kid:
                    key = k
                    break
            
            if not key:
                return None
            
            # 토큰 검증
            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=self.issuer,
            )
            
            return payload
            
        except JWTError:
            return None
    
    def verify_token_sync(self, token: str) -> Optional[Dict[str, Any]]:
        """
        JWT 토큰을 검증합니다 (동기).
        
        Args:
            token: JWT 액세스 토큰
            
        Returns:
            검증된 토큰 페이로드 또는 None
        """
        try:
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            
            if not kid:
                return None
            
            jwks = self._get_jwks_sync()
            key = None
            for k in jwks.get("keys", []):
                if k.get("kid") == kid:
                    key = k
                    break
            
            if not key:
                return None
            
            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=self.issuer,
            )
            
            return payload
            
        except JWTError:
            return None
    
    def get_user_info(self, access_token: str) -> Optional[UserInfo]:
        """
        액세스 토큰으로 사용자 정보를 가져옵니다.
        
        Args:
            access_token: Cognito 액세스 토큰
            
        Returns:
            사용자 정보 또는 None
        """
        try:
            response = self.client.get_user(AccessToken=access_token)
            
            attributes = {
                attr["Name"]: attr["Value"]
                for attr in response.get("UserAttributes", [])
            }
            
            return UserInfo(
                user_id=attributes.get("sub", ""),
                email=attributes.get("email", ""),
                nickname=attributes.get("preferred_username", attributes.get("nickname", ""))
            )
            
        except Exception:
            return None
    
    def get_user_by_sub(self, sub: str) -> Optional[UserInfo]:
        """
        Cognito sub 값으로 사용자 정보를 가져옵니다.
        
        Args:
            sub: Cognito 사용자 sub
            
        Returns:
            사용자 정보 또는 None
        """
        try:
            response = self.client.admin_get_user(
                UserPoolId=self.user_pool_id,
                Username=sub
            )
            
            attributes = {
                attr["Name"]: attr["Value"]
                for attr in response.get("UserAttributes", [])
            }
            
            return UserInfo(
                user_id=attributes.get("sub", ""),
                email=attributes.get("email", ""),
                nickname=attributes.get("preferred_username", attributes.get("nickname", ""))
            )
            
        except Exception:
            return None
    
    def get_user_by_nickname(self, nickname: str) -> Optional[UserInfo]:
        """
        닉네임(preferred_username)으로 사용자를 찾습니다.
        
        Args:
            nickname: 사용자 닉네임
            
        Returns:
            사용자 정보 또는 None
        """
        try:
            response = self.client.list_users(
                UserPoolId=self.user_pool_id,
                Filter=f'preferred_username = "{nickname}"',
                Limit=1
            )
            
            users = response.get("Users", [])
            if not users:
                return None
            
            user = users[0]
            attributes = {
                attr["Name"]: attr["Value"]
                for attr in user.get("Attributes", [])
            }
            
            return UserInfo(
                user_id=attributes.get("sub", ""),
                email=attributes.get("email", ""),
                nickname=attributes.get("preferred_username", attributes.get("nickname", ""))
            )
            
        except Exception:
            return None


@lru_cache()
def get_cognito_service() -> CognitoService:
    """Cognito 서비스 싱글톤 인스턴스 반환"""
    return CognitoService()
