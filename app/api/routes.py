"""
API Routes
Fproject-agent 패턴에 맞춘 중앙 라우터
"""
from fastapi import APIRouter
from app.api.endpoints import health, report

router = APIRouter()

# All endpoints under /report prefix
router.include_router(health.router, prefix="/report", tags=["health"])
router.include_router(report.router, prefix="/report", tags=["report"])
