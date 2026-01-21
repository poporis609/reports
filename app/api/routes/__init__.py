# API Routes (Legacy - 새 구조는 app.api.routes 사용)
# 하위 호환성을 위해 유지
from app.api.endpoints.report import router as report_router

__all__ = [
    "report_router"
]
