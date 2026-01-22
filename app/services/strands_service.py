# app/services/strands_service.py
"""
감정 분석 서비스 - Fproject-agent API 호출
Bedrock 직접 호출 대신 Fproject-agent의 /agent/report 엔드포인트를 사용
"""
import json
import re
import logging
import httpx
from typing import Dict, Any, List
from datetime import date
from functools import lru_cache
from dataclasses import dataclass

from app.config.settings import get_settings

logger = logging.getLogger(__name__)

# Fproject-agent API 엔드포인트
AGENT_API_URL = "https://api.aws11.shop/agent/report"


class StrandsServiceError(Exception):
    """감정 분석 서비스 에러"""
    pass


@dataclass
class DailyScore:
    """일별 감정 점수"""
    date: str
    score: float
    sentiment: str
    key_themes: List[str]


@dataclass
class SentimentAnalysis:
    """감정 분석 결과"""
    daily_scores: List[DailyScore]
    positive_patterns: List[str]
    negative_patterns: List[str]
    recommendations: List[str]


class StrandsAgentService:
    """Fproject-agent API를 사용한 감정 분석 서비스"""
    
    def __init__(self):
        self.settings = get_settings()
        self.api_url = AGENT_API_URL
        self.timeout = 120.0  # AI 분석에 시간이 걸릴 수 있으므로 타임아웃 늘림
    
    def analyze_sentiment(
        self,
        entries: List[Dict[str, Any]],
        nickname: str,
        user_id: str = None,
        start_date: str = None,
        end_date: str = None
    ) -> SentimentAnalysis:
        """
        일기 항목들의 감정을 분석합니다.
        Fproject-agent API를 호출하여 분석 수행
        """
        # 일기 내용 포맷팅
        diary_texts = []
        for entry in entries:
            record_date = entry.get("record_date", "")
            if isinstance(record_date, date):
                record_date = record_date.isoformat()
            content = entry.get("content", "")
            diary_texts.append(f"[{record_date}] {content}")
        
        # API 요청 본문 구성
        request_content = f"""
{nickname}님의 일주일 일기를 분석해주세요.

## 일기 내용
{chr(10).join(diary_texts)}

## 분석 요청
1. 각 일기의 감정 점수 (1-10점)
2. 긍정적/부정적 패턴 식별
3. 개인화된 피드백 제공

응답은 반드시 JSON 형식으로 해주세요:
{{
  "average_score": 6.5,
  "evaluation": "positive",
  "daily_analysis": [
    {{"date": "2026-01-13", "score": 7, "sentiment": "긍정적", "key_themes": ["테마1", "테마2"]}}
  ],
  "patterns": [
    {{"type": "activity", "value": "활동명", "correlation": "positive"}}
  ],
  "feedback": ["피드백1", "피드백2"]
}}
"""
        
        request_body = {
            "content": request_content,
            "user_id": user_id,
            "start_date": start_date,
            "end_date": end_date
        }
        
        logger.info(f"Fproject-agent API 호출 시작: {nickname}, user_id={user_id}")
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    self.api_url,
                    json=request_body,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Fproject-agent API 응답: success={result.get('success')}")
                
                if result.get("success"):
                    # 응답에서 분석 결과 추출
                    return self._parse_agent_response(result.get("response", ""), entries)
                else:
                    logger.error(f"Agent API 오류: {result.get('error')}")
                    return self._default_analysis(entries)
                    
        except httpx.TimeoutException:
            logger.error("Fproject-agent API 타임아웃")
            return self._default_analysis(entries)
        except httpx.HTTPStatusError as e:
            logger.error(f"Fproject-agent API HTTP 오류: {e.response.status_code}")
            return self._default_analysis(entries)
        except Exception as e:
            logger.error(f"Fproject-agent API 호출 실패: {e}")
            return self._default_analysis(entries)
    
    def _parse_agent_response(
        self,
        response: str,
        entries: List[Dict[str, Any]]
    ) -> SentimentAnalysis:
        """Agent API 응답을 SentimentAnalysis로 파싱합니다."""
        
        try:
            # JSON 블록 추출 시도
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if json_match:
                json_str = json_match.group(1)
                data = json.loads(json_str)
            else:
                # ```json 없이 직접 JSON 찾기
                json_match = re.search(r'\{[\s\S]*"daily_analysis"[\s\S]*\}', response)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    # JSON이 없으면 텍스트 응답에서 정보 추출 시도
                    logger.warning("JSON 형식 응답 없음, 기본 분석 사용")
                    return self._default_analysis(entries)
            
            # daily_scores 생성
            daily_scores = []
            for item in data.get("daily_analysis", []):
                daily_scores.append(DailyScore(
                    date=item.get("date", ""),
                    score=float(item.get("score", 5)),
                    sentiment=item.get("sentiment", "분석 완료"),
                    key_themes=item.get("key_themes", [])
                ))
            
            # 패턴 추출
            positive_patterns = []
            negative_patterns = []
            for pattern in data.get("patterns", []):
                pattern_str = f"{pattern.get('value', '')} ({pattern.get('type', '')})"
                if pattern.get("correlation") == "positive":
                    positive_patterns.append(pattern_str)
                else:
                    negative_patterns.append(pattern_str)
            
            return SentimentAnalysis(
                daily_scores=daily_scores,
                positive_patterns=positive_patterns,
                negative_patterns=negative_patterns,
                recommendations=data.get("feedback", [])
            )
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"응답 파싱 실패: {e}")
            return self._default_analysis(entries)
    
    def _default_analysis(self, entries: List[Dict[str, Any]]) -> SentimentAnalysis:
        """기본 분석 결과 반환 (API 실패 시)"""
        daily_scores = []
        for entry in entries:
            record_date = entry.get("record_date", "")
            if isinstance(record_date, date):
                record_date = record_date.isoformat()
            daily_scores.append(DailyScore(
                date=record_date,
                score=5.0,
                sentiment="분석 대기",
                key_themes=entry.get("tags", []) or []
            ))
        
        return SentimentAnalysis(
            daily_scores=daily_scores,
            positive_patterns=[],
            negative_patterns=[],
            recommendations=["AI 분석 서비스에 일시적인 문제가 있습니다. 잠시 후 다시 시도해주세요."]
        )


@lru_cache()
def get_strands_service() -> StrandsAgentService:
    """감정 분석 서비스 싱글톤 인스턴스 반환"""
    return StrandsAgentService()
