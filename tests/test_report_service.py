"""
ReportAnalysisService 테스트
"""
import pytest
from datetime import date, timedelta
from app.services.report_service import (
    ReportAnalysisService,
    DailyAnalysisResult,
    PatternResult,
    WeeklyReportResult,
)
from app.services.strands_service import DailyScore, SentimentAnalysis


class TestReportAnalysisService:
    """ReportAnalysisService 테스트"""
    
    @pytest.fixture
    def service(self):
        return ReportAnalysisService()
    
    @pytest.fixture
    def sample_daily_scores(self):
        """샘플 일별 점수"""
        return [
            DailyScore(date="2025-01-13", score=7.5, sentiment="positive", key_themes=["운동"]),
            DailyScore(date="2025-01-14", score=6.0, sentiment="neutral", key_themes=["독서"]),
            DailyScore(date="2025-01-15", score=8.0, sentiment="positive", key_themes=["친구"]),
            DailyScore(date="2025-01-16", score=4.0, sentiment="negative", key_themes=["스트레스"]),
            DailyScore(date="2025-01-17", score=5.5, sentiment="neutral", key_themes=["일상"]),
        ]
    
    @pytest.fixture
    def sample_entries(self):
        """샘플 일기 항목"""
        return [
            {"id": 1, "content": "오늘 운동을 했다. 기분이 좋다.", "record_date": date(2025, 1, 13), "tags": ["운동", "맑음"]},
            {"id": 2, "content": "책을 읽었다.", "record_date": date(2025, 1, 14), "tags": ["독서"]},
            {"id": 3, "content": "친구를 만났다. 즐거웠다.", "record_date": date(2025, 1, 15), "tags": ["친구", "맑음"]},
            {"id": 4, "content": "일이 많아서 힘들었다.", "record_date": date(2025, 1, 16), "tags": ["스트레스", "흐림"]},
            {"id": 5, "content": "평범한 하루였다.", "record_date": date(2025, 1, 17), "tags": ["일상"]},
        ]
    
    def test_calculate_average_score(self, service, sample_daily_scores):
        """평균 점수 계산 테스트"""
        avg = service.calculate_average_score(sample_daily_scores)
        expected = (7.5 + 6.0 + 8.0 + 4.0 + 5.5) / 5
        assert avg == round(expected, 1)
    
    def test_calculate_average_score_empty(self, service):
        """빈 목록의 평균 점수 계산"""
        avg = service.calculate_average_score([])
        assert avg == 0.0
    
    def test_determine_evaluation_type_positive(self, service):
        """긍정 평가 유형 결정"""
        assert service.determine_evaluation_type(7.0) == "positive"
        assert service.determine_evaluation_type(5.0) == "positive"
    
    def test_determine_evaluation_type_negative(self, service):
        """부정 평가 유형 결정"""
        assert service.determine_evaluation_type(4.9) == "negative"
        assert service.determine_evaluation_type(1.0) == "negative"
    
    def test_identify_extreme_days_positive(self, service, sample_daily_scores):
        """긍정 평가 시 극단적인 날 식별"""
        extreme = service.identify_extreme_days(sample_daily_scores, "positive")
        assert len(extreme) == 3
        assert extreme[0].score == 8.0  # 가장 높은 점수
        assert extreme[1].score == 7.5
    
    def test_identify_extreme_days_negative(self, service, sample_daily_scores):
        """부정 평가 시 극단적인 날 식별"""
        extreme = service.identify_extreme_days(sample_daily_scores, "negative")
        assert len(extreme) == 3
        assert extreme[0].score == 4.0  # 가장 낮은 점수
    
    def test_identify_patterns(self, service, sample_entries, sample_daily_scores):
        """패턴 식별 테스트"""
        patterns = service.identify_patterns(sample_entries, sample_daily_scores)
        assert len(patterns) > 0
        
        # 맑음 태그가 높은 점수와 연관되어야 함
        sunny_pattern = next((p for p in patterns if p.value == "맑음"), None)
        if sunny_pattern:
            assert sunny_pattern.correlation == "positive"
    
    def test_infer_tag_type(self, service):
        """태그 유형 추론 테스트"""
        assert service._infer_tag_type("맑음") == "weather"
        assert service._infer_tag_type("비") == "weather"
        assert service._infer_tag_type("운동") == "activity"
        assert service._infer_tag_type("산책") == "activity"
        assert service._infer_tag_type("친구") == "experience"
    
    def test_get_week_range(self, service):
        """주간 범위 계산 테스트"""
        # 2025-01-15 (수요일)
        test_date = date(2025, 1, 15)
        week_start, week_end = service.get_week_range(test_date)
        
        assert week_start == date(2025, 1, 13)  # 월요일
        assert week_end == date(2025, 1, 19)    # 일요일
        assert week_start.weekday() == 0  # 월요일
        assert week_end.weekday() == 6    # 일요일
    
    def test_get_previous_week_range(self, service):
        """지난 주 범위 계산 테스트"""
        week_start, week_end = service.get_previous_week_range()
        
        assert week_start.weekday() == 0  # 월요일
        assert week_end.weekday() == 6    # 일요일
        assert (week_end - week_start).days == 6
    
    def test_generate_feedback(self, service, sample_entries, sample_daily_scores):
        """피드백 생성 테스트"""
        patterns = service.identify_patterns(sample_entries, sample_daily_scores)
        feedback = service.generate_feedback(
            sample_entries, sample_daily_scores, patterns, "positive"
        )
        
        assert len(feedback) > 0
        assert any("긍정" in f for f in feedback)
    
    def test_generate_report(self, service, sample_entries, sample_daily_scores):
        """리포트 생성 테스트"""
        analysis = SentimentAnalysis(
            daily_scores=sample_daily_scores,
            positive_patterns=["운동 (activity)"],
            negative_patterns=["스트레스 (experience)"],
            recommendations=["좋은 습관을 유지하세요."]
        )
        
        report = service.generate_report(
            user_id="test-user-123",
            nickname="테스트유저",
            week_start=date(2025, 1, 13),
            week_end=date(2025, 1, 19),
            entries=sample_entries,
            analysis=analysis
        )
        
        assert report.user_id == "test-user-123"
        assert report.nickname == "테스트유저"
        assert report.average_score > 0
        assert report.evaluation in ["positive", "negative"]
        assert len(report.daily_analysis) == len(sample_daily_scores)
        assert len(report.feedback) > 0


class TestDailyAnalysisResult:
    """DailyAnalysisResult 테스트"""
    
    def test_to_dict(self):
        """딕셔너리 변환 테스트"""
        result = DailyAnalysisResult(
            date="2025-01-13",
            score=7.5,
            sentiment="positive",
            diary_content="오늘 좋은 하루였다.",
            key_themes=["운동", "친구"]
        )
        
        d = result.to_dict()
        assert d["date"] == "2025-01-13"
        assert d["score"] == 7.5
        assert d["sentiment"] == "positive"
        assert d["key_themes"] == ["운동", "친구"]


class TestPatternResult:
    """PatternResult 테스트"""
    
    def test_to_dict(self):
        """딕셔너리 변환 테스트"""
        pattern = PatternResult(
            type="activity",
            value="운동",
            correlation="positive",
            frequency=3,
            average_score=7.5
        )
        
        d = pattern.to_dict()
        assert d["type"] == "activity"
        assert d["value"] == "운동"
        assert d["correlation"] == "positive"
        assert d["frequency"] == 3
