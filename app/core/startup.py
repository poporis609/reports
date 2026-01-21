"""
Application Startup Handler
Fproject-agent 패턴에 맞춘 시작 핸들러
"""
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

# 전역 서비스 인스턴스
_services = {}


async def startup_handler():
    """애플리케이션 시작 시 초기화"""
    print("=" * 80)
    print("🔧 FastAPI 초기화 중...")
    print("=" * 80)
    
    # 설정 로드
    try:
        print(f"✅ 설정 로드 완료")
        print(f"   - App Name: {settings.APP_NAME}")
        print(f"   - Version: {settings.VERSION}")
        print(f"   - AWS Region: {settings.AWS_REGION}")
        print(f"   - Debug Mode: {settings.DEBUG}")
    except Exception as e:
        print(f"⚠️  설정 로드 실패: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # 데이터베이스 연결 확인
    try:
        from app.config.database import engine
        print("✅ 데이터베이스 연결 준비 완료")
    except Exception as e:
        print(f"⚠️  데이터베이스 연결 실패: {str(e)}")
    
    # 서비스 초기화
    try:
        from app.services.strands_service import get_strands_service
        _services['strands'] = get_strands_service()
        print("✅ Strands Agent 서비스 로드 완료")
    except Exception as e:
        print(f"⚠️  Strands Agent 서비스 로드 실패: {str(e)}")
    
    print("=" * 80)
    print("🚀 초기화 완료")
    print("=" * 80)


def get_service(name: str):
    """서비스 인스턴스 반환"""
    return _services.get(name)
