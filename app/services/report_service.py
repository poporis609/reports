"""
리포트 분석 서비스 - 주간 리포트 생성 및 분석
"""
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict

from app.services.strands_service import SentimentAnalysis, DailyScore


@dataclass
class DailyAnalysisResult:
    """일별 분석 결과"""
    date: str
    score: float
    sentiment: str
    diary_content: str
    key_themes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PatternResult:
    """패턴 분석 결과"""
    type: str           # 'activity' | 'experience' | 'weather'
    value: str
    correlation: str    # 'positive' | 'negative'
    frequency: int
    average_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WeeklyReportResult:
    """주간 리포트 결과"""
    user_id: str
    nickname: str
    week_start: date
    week_end: date
    average_score: float
    evaluation: str
    daily_analysis: List[DailyAnalysisResult]
    patterns: List[PatternResult]
    feedback: List[str]
    has_partial_data: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "nickname": self.nickname,
            "week_start": self.week_start.isoformat(),
            "week_end": self.week_end.isoformat(),
            "average_score": self.average_score,
            "evaluation": self.evaluation,
            "daily_analysis": [d.to_dict() for d in self.daily_analysis],
            "patterns": [p.to_dict() for p in self.patterns],
            "feedback": self.feedback,
            "has_partial_data": self.has_partial_data,
        }


class ReportAnalysisService:
    """주간 리포트 분석 서비스"""
    
    SCORE_THRESHOLD = 5.0  # 긍정/부정 평가 기준점
    
    def calculate_average_score(self, daily_scores: List[DailyScore]) -> float:
        """
        일별 점수의 평균을 계산합니다.
        
        Args:
            daily_scores: 일별 점수 목록
            
        Returns:
            평균 점수 (소수점 1자리)
        """
        if not daily_scores:
            return 0.0
        
        total = sum(score.score for score in daily_scores)
        average = total / len(daily_scores)
        return round(average, 1)
    
    def determine_evaluation_type(self, average_score: float) -> str:
        """
        평균 점수를 기반으로 평가 유형을 결정합니다.
        
        Args:
            average_score: 평균 점수
            
        Returns:
            'positive' 또는 'negative'
        """
        return "positive" if average_score >= self.SCORE_THRESHOLD else "negative"
    
    def identify_extreme_days(
        self,
        daily_scores: List[DailyScore],
        evaluation: str
    ) -> List[DailyScore]:
        """
        극단적인 점수의 날을 식별합니다.
        
        Args:
            daily_scores: 일별 점수 목록
            evaluation: 평가 유형
            
        Returns:
            극단적인 점수의 날 목록 (최대 3개)
        """
        if not daily_scores:
            return []
        
        sorted_scores = sorted(
            daily_scores,
            key=lambda x: x.score,
            reverse=(evaluation == "positive")
        )
        
        return sorted_scores[:3]
    
    def identify_patterns(
        self,
        entries: List[Dict[str, Any]],
        daily_scores: List[DailyScore]
    ) -> List[PatternResult]:
        """
        활동/날씨와 점수 간의 패턴을 식별합니다.
        
        Args:
            entries: 일기 항목 목록
            daily_scores: 일별 점수 목록
            
        Returns:
            패턴 목록
        """
        # 날짜별 점수 매핑
        date_to_score = {}
        for score in daily_scores:
            date_to_score[score.date] = score.score
        
        # 태그별 점수 수집
        tag_scores: Dict[str, List[float]] = defaultdict(list)
        
        for entry in entries:
            record_date = entry.get("record_date", "")
            if isinstance(record_date, date):
                record_date = record_date.isoformat()
            
            score = date_to_score.get(record_date, 5.0)
            tags = entry.get("tags") or []
            
            for tag in tags:
                tag_scores[tag].append(score)
        
        # 패턴 생성
        patterns = []
        for tag, scores in tag_scores.items():
            if len(scores) >= 1:  # 최소 1회 이상 등장
                avg_score = sum(scores) / len(scores)
                correlation = "positive" if avg_score >= self.SCORE_THRESHOLD else "negative"
                
                # 태그 유형 추론
                tag_type = self._infer_tag_type(tag)
                
                patterns.append(PatternResult(
                    type=tag_type,
                    value=tag,
                    correlation=correlation,
                    frequency=len(scores),
                    average_score=round(avg_score, 1)
                ))
        
        # 영향력(빈도 × 점수 편차)으로 정렬
        patterns.sort(
            key=lambda p: p.frequency * abs(p.average_score - self.SCORE_THRESHOLD),
            reverse=True
        )
        
        return patterns[:10]  # 상위 10개만 반환
    
    def _infer_tag_type(self, tag: str) -> str:
        """태그 유형을 추론합니다."""
        weather_keywords = ["맑음", "흐림", "비", "눈", "더움", "추움", "날씨"]
        activity_keywords = ["운동", "산책", "독서", "영화", "게임", "요리", "청소"]
        
        tag_lower = tag.lower()
        
        for keyword in weather_keywords:
            if keyword in tag_lower:
                return "weather"
        
        for keyword in activity_keywords:
            if keyword in tag_lower:
                return "activity"
        
        return "experience"
    
    def extract_themes(
        self,
        entries: List[Dict[str, Any]],
        daily_scores: List[DailyScore],
        evaluation: str
    ) -> List[str]:
        """
        일기 항목에서 공통 테마를 추출합니다.
        
        Args:
            entries: 일기 항목 목록
            daily_scores: 일별 점수 목록
            evaluation: 평가 유형
            
        Returns:
            공통 테마 목록
        """
        # 날짜별 점수 매핑
        date_to_score = {s.date: s.score for s in daily_scores}
        
        # 평가 유형에 따라 필터링
        threshold = self.SCORE_THRESHOLD
        relevant_entries = []
        
        for entry in entries:
            record_date = entry.get("record_date", "")
            if isinstance(record_date, date):
                record_date = record_date.isoformat()
            
            score = date_to_score.get(record_date, 5.0)
            
            if evaluation == "positive" and score >= threshold:
                relevant_entries.append(entry)
            elif evaluation == "negative" and score < threshold:
                relevant_entries.append(entry)
        
        # 테마 수집
        theme_count: Dict[str, int] = defaultdict(int)
        for entry in relevant_entries:
            tags = entry.get("tags") or []
            for tag in tags:
                theme_count[tag] += 1
        
        # 빈도순 정렬
        sorted_themes = sorted(theme_count.items(), key=lambda x: x[1], reverse=True)
        return [theme for theme, _ in sorted_themes[:5]]
    
    def generate_feedback(
        self,
        entries: List[Dict[str, Any]],
        daily_scores: List[DailyScore],
        patterns: List[PatternResult],
        evaluation: str
    ) -> List[str]:
        """
        피드백을 생성합니다.
        
        Args:
            entries: 일기 항목 목록
            daily_scores: 일별 점수 목록
            patterns: 패턴 목록
            evaluation: 평가 유형
            
        Returns:
            피드백 목록
        """
        feedback = []
        
        # 극단적인 날 식별
        extreme_days = self.identify_extreme_days(daily_scores, evaluation)
        
        # 극단적인 날에 대한 피드백
        for day in extreme_days[:2]:
            if evaluation == "positive":
                feedback.append(
                    f"{day.date}에 감정 점수가 {day.score}점으로 높았습니다. "
                    f"이 날의 긍정적인 경험을 기억하세요."
                )
            else:
                feedback.append(
                    f"{day.date}에 감정 점수가 {day.score}점으로 낮았습니다. "
                    f"이 날 무엇이 힘들었는지 돌아보세요."
                )
        
        # 패턴 기반 피드백
        for pattern in patterns[:3]:
            if pattern.correlation == "positive":
                feedback.append(
                    f"'{pattern.value}' 활동이 {pattern.frequency}회 있었고, "
                    f"평균 점수가 {pattern.average_score}점으로 높았습니다. "
                    f"이 활동을 계속 유지하세요."
                )
            else:
                feedback.append(
                    f"'{pattern.value}' 관련 날의 평균 점수가 {pattern.average_score}점으로 낮았습니다. "
                    f"이 상황에서 스트레스를 줄일 방법을 찾아보세요."
                )
        
        # 전반적인 피드백
        if evaluation == "positive":
            feedback.append(
                "이번 주는 전반적으로 긍정적인 한 주였습니다. "
                "좋은 습관을 계속 유지하세요!"
            )
        else:
            feedback.append(
                "이번 주는 다소 힘든 한 주였을 수 있습니다. "
                "충분한 휴식과 자기 돌봄을 권장합니다."
            )
        
        return feedback
    
    def generate_report(
        self,
        user_id: str,
        nickname: str,
        week_start: date,
        week_end: date,
        entries: List[Dict[str, Any]],
        analysis: SentimentAnalysis
    ) -> WeeklyReportResult:
        """
        주간 리포트를 생성합니다.
        
        Args:
            user_id: 사용자 ID
            nickname: 닉네임
            week_start: 주 시작일
            week_end: 주 종료일
            entries: 일기 항목 목록
            analysis: Bedrock 감정 분석 결과
            
        Returns:
            주간 리포트 결과
        """
        # 평균 점수 계산
        average_score = self.calculate_average_score(analysis.daily_scores)
        
        # 평가 유형 결정
        evaluation = self.determine_evaluation_type(average_score)
        
        # 일별 분석 결과 생성
        daily_analysis = self._create_daily_analysis(entries, analysis.daily_scores)
        
        # 패턴 식별
        patterns = self.identify_patterns(entries, analysis.daily_scores)
        
        # 피드백 생성
        feedback = self.generate_feedback(
            entries, analysis.daily_scores, patterns, evaluation
        )
        
        # Bedrock 추천사항 추가
        if analysis.recommendations:
            feedback.extend(analysis.recommendations)
        
        # 부분 데이터 여부 확인
        days_in_week = (week_end - week_start).days + 1
        has_partial_data = len(entries) < days_in_week
        
        if has_partial_data:
            feedback.insert(0, 
                f"⚠️ 이번 주 {days_in_week}일 중 {len(entries)}일의 일기만 분석되었습니다."
            )
        
        return WeeklyReportResult(
            user_id=user_id,
            nickname=nickname,
            week_start=week_start,
            week_end=week_end,
            average_score=average_score,
            evaluation=evaluation,
            daily_analysis=daily_analysis,
            patterns=patterns,
            feedback=feedback,
            has_partial_data=has_partial_data
        )
    
    def _create_daily_analysis(
        self,
        entries: List[Dict[str, Any]],
        daily_scores: List[DailyScore]
    ) -> List[DailyAnalysisResult]:
        """일별 분석 결과를 생성합니다."""
        # 날짜별 일기 매핑
        date_to_entry = {}
        for entry in entries:
            record_date = entry.get("record_date", "")
            if isinstance(record_date, date):
                record_date = record_date.isoformat()
            date_to_entry[record_date] = entry
        
        results = []
        for score in daily_scores:
            entry = date_to_entry.get(score.date, {})
            content = entry.get("content", "")
            
            # 내용 요약 (처음 100자)
            summary = content[:100] + "..." if len(content) > 100 else content
            
            results.append(DailyAnalysisResult(
                date=score.date,
                score=score.score,
                sentiment=score.sentiment,
                diary_content=summary,
                key_themes=score.key_themes
            ))
        
        return results
    
    @staticmethod
    def get_week_range(target_date: Optional[date] = None) -> Tuple[date, date]:
        """
        주어진 날짜가 속한 주의 시작일(월요일)과 종료일(일요일)을 반환합니다.
        
        Args:
            target_date: 대상 날짜 (기본값: 오늘)
            
        Returns:
            (주 시작일, 주 종료일) 튜플
        """
        if target_date is None:
            target_date = date.today()
        
        # 월요일 찾기 (weekday: 0=월, 6=일)
        days_since_monday = target_date.weekday()
        week_start = target_date - timedelta(days=days_since_monday)
        week_end = week_start + timedelta(days=6)
        
        return week_start, week_end
    
    @staticmethod
    def get_previous_week_range() -> Tuple[date, date]:
        """
        지난 주의 시작일(월요일)과 종료일(일요일)을 반환합니다.
        
        Returns:
            (주 시작일, 주 종료일) 튜플
        """
        today = date.today()
        days_since_monday = today.weekday()
        this_monday = today - timedelta(days=days_since_monday)
        last_monday = this_monday - timedelta(days=7)
        last_sunday = last_monday + timedelta(days=6)
        
        return last_monday, last_sunday
