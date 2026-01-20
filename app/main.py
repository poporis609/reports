"""
Weekly Report Service - FastAPI 메인 애플리케이션
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import get_settings
from app.api.routes import report_router

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="주간 일기 분석 및 감정 리포트 서비스",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 설정
allowed_origins = [
    "https://aws11.shop",
    "https://api.aws11.shop",
    "https://www.aws11.shop",
]

# 개발 환경에서만 localhost 허용
if settings.DEBUG:
    allowed_origins.extend([
        "http://localhost:3000",
        "http://localhost:8000",
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Report API 라우터
app.include_router(report_router)


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy", "service": settings.APP_NAME}


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "주간 일기 분석 및 감정 리포트 서비스"
    }
