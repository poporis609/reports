"""
ReportRepository 테스트
"""
import pytest
from datetime import date, datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.weekly_report import WeeklyReport
from app.repositories.report_repository import ReportRepository


@pytest.fixture(scope="function")
def test_db():
    """테스트용 인메모리 SQLite 데이터베이스"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def report_repo(test_db):
    """ReportRepository 인스턴스"""
    return ReportRepository(test_db)


@pytest.fixture
def sample_report_data():
    """샘플 리포트 데이터"""
    return {
        "user_id": "test-user-123",
        "nickname": "테스트유저",
        "week_start": date(2025, 1, 13),
        "week_end": date(2025, 1, 19),
        "average_score": 6.5,
        "evaluation": "positive",
        "daily_analysis": [
            {"date": "2025-01-13", "score": 7.5, "sentiment": "positive", "diary_content": "좋은 하루"}
        ],
        "patterns": [
            {"type": "activity", "value": "운동", "correlation": "positive", "frequency": 3, "average_score": 7.5}
        ],
        "feedback": ["좋은 습관을 유지하세요."],
        "s3_key": None,
        "status": "completed"
    }


class TestReportRepository:
    """ReportRepository 테스트"""
    
    def test_save_report(self, report_repo, sample_report_data):
        """리포트 저장 테스트"""
        report = report_repo.save_report(**sample_report_data)
        
        assert report.id is not None
        assert report.user_id == sample_report_data["user_id"]
        assert report.nickname == sample_report_data["nickname"]
        assert report.average_score == sample_report_data["average_score"]
        assert report.evaluation == sample_report_data["evaluation"]
        assert report.status == "completed"
    
    def test_get_report_by_id(self, report_repo, sample_report_data):
        """ID로 리포트 조회 테스트"""
        saved = report_repo.save_report(**sample_report_data)
        
        found = report_repo.get_report_by_id(saved.id)
        assert found is not None
        assert found.id == saved.id
        assert found.user_id == saved.user_id
    
    def test_get_report_by_id_not_found(self, report_repo):
        """존재하지 않는 ID 조회"""
        found = report_repo.get_report_by_id(99999)
        assert found is None
    
    def test_get_latest_report_by_user(self, report_repo, sample_report_data):
        """사용자의 최신 리포트 조회"""
        # 첫 번째 리포트
        report_repo.save_report(**sample_report_data)
        
        # 두 번째 리포트 (다른 주)
        sample_report_data["week_start"] = date(2025, 1, 20)
        sample_report_data["week_end"] = date(2025, 1, 26)
        second = report_repo.save_report(**sample_report_data)
        
        latest = report_repo.get_latest_report_by_user("test-user-123")
        assert latest is not None
        assert latest.id == second.id
    
    def test_get_report_by_nickname(self, report_repo, sample_report_data):
        """닉네임으로 리포트 조회"""
        report_repo.save_report(**sample_report_data)
        
        found = report_repo.get_report_by_nickname("테스트유저")
        assert found is not None
        assert found.nickname == "테스트유저"
    
    def test_get_reports_by_user(self, report_repo, sample_report_data):
        """사용자의 리포트 목록 조회"""
        # 여러 리포트 저장
        report_repo.save_report(**sample_report_data)
        
        sample_report_data["week_start"] = date(2025, 1, 20)
        sample_report_data["week_end"] = date(2025, 1, 26)
        report_repo.save_report(**sample_report_data)
        
        reports = report_repo.get_reports_by_user("test-user-123")
        assert len(reports) == 2
    
    def test_get_reports_by_user_with_limit(self, report_repo, sample_report_data):
        """리포트 목록 조회 (limit)"""
        for i in range(5):
            sample_report_data["week_start"] = date(2025, 1, 13 + i * 7)
            sample_report_data["week_end"] = date(2025, 1, 19 + i * 7)
            report_repo.save_report(**sample_report_data)
        
        reports = report_repo.get_reports_by_user("test-user-123", limit=3)
        assert len(reports) == 3
    
    def test_report_exists_for_week(self, report_repo, sample_report_data):
        """해당 주 리포트 존재 여부 확인"""
        report_repo.save_report(**sample_report_data)
        
        exists = report_repo.report_exists_for_week(
            "test-user-123",
            date(2025, 1, 13),
            date(2025, 1, 19)
        )
        assert exists is True
        
        not_exists = report_repo.report_exists_for_week(
            "test-user-123",
            date(2025, 1, 20),
            date(2025, 1, 26)
        )
        assert not_exists is False
    
    def test_update_report(self, report_repo, sample_report_data):
        """리포트 업데이트 테스트"""
        saved = report_repo.save_report(**sample_report_data)
        
        updated = report_repo.update_report(
            report_id=saved.id,
            average_score=8.0,
            evaluation="positive",
            daily_analysis=[{"date": "2025-01-13", "score": 8.0}],
            patterns=[],
            feedback=["업데이트된 피드백"],
            s3_key="reports/test.json",
            status="completed"
        )
        
        assert updated is not None
        assert updated.average_score == 8.0
        assert updated.s3_key == "reports/test.json"
    
    def test_update_report_status(self, report_repo, sample_report_data):
        """리포트 상태 업데이트 테스트"""
        sample_report_data["status"] = "processing"
        saved = report_repo.save_report(**sample_report_data)
        
        updated = report_repo.update_report_status(saved.id, "completed")
        assert updated.status == "completed"
        
        failed = report_repo.update_report_status(saved.id, "failed", "에러 발생")
        assert failed.status == "failed"
        assert "에러 발생" in failed.feedback


class TestWeeklyReportModel:
    """WeeklyReport 모델 테스트"""
    
    def test_to_dict(self, report_repo, sample_report_data):
        """to_dict 메서드 테스트"""
        report = report_repo.save_report(**sample_report_data)
        
        d = report.to_dict()
        assert d["id"] == report.id
        assert d["user_id"] == "test-user-123"
        assert d["nickname"] == "테스트유저"
        assert d["week_start"] == "2025-01-13"
        assert d["week_end"] == "2025-01-19"
        assert d["average_score"] == 6.5
        assert d["evaluation"] == "positive"
        assert d["status"] == "completed"
        assert "created_at" in d
