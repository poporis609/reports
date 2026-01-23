"""
FastAPI Application Entry Point
Fproject-agent 패턴에 맞춘 메인 애플리케이션
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.startup import startup_handler
from app.api.router import router
from app.tracing import setup_tracing

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프사이클 관리"""
    # Startup
    setup_tracing("weekly-report")
    HTTPXClientInstrumentor().instrument()
    await startup_handler()
    yield
    # Shutdown (필요시 정리 로직 추가)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="주간 일기 분석 및 감정 리포트 서비스",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# CORS 설정
allowed_origins = [
    "https://aws11.shop",
    "https://api.aws11.shop",
    "https://www.aws11.shop",
    "https://web.aws11.shop",
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

# Include routers
app.include_router(router)

# FastAPI Instrumentor 적용
FastAPIInstrumentor.instrument_app(app)


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트 (K8s liveness/readiness probe용)"""
    return {"status": "healthy", "service": settings.APP_NAME}


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "description": "주간 일기 분석 및 감정 리포트 서비스"
    }
