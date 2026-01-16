# app/services/strands_service.py
"""
Strands Agent 서비스 - Bedrock Flow 대체
"""
import json
import re
import logging
from typing import Dict, Any, List
from datetime import date
from functools import lru_cache

from strands import Agent
from strands.models import BedrockModel

from app.config.settings import get_settings
from app.services.bedrock_service import SentimentAnalysis, DailyScore

logger = logging.getLogger(__name__)


class StrandsServiceError(Exception):
    """Strands 서비스 에러"""
    pass


class StrandsAgentService:
    """Strands Agent를 사용한 감정 분석 서비스"""
    
    def __init__(self):
        self.settings = get_settings()
        
        # Claude Sonnet 4.5 모델 (Bedrock) - inference profile 사용
        self.model = BedrockModel(
            model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
            region_name=self.settings.AWS_REGION
        )
        
        # Agent 생성
        self.agent = Agent(
            model=self.model,
            system_prompt=self._get_system_prompt()
        )
    
    def _get_system_prompt(self) -> str:
        return """
당신은 감정 분석 전문가입니다. 일기 내용을 분석하여 다음을 수행합니다:

1. 각 일기의 감정 점수(1-10) 산출
2. 주요 감정 상태 파악
3. 긍정/부정 패턴 발견
4. 따뜻하고 공감적인 피드백 제공

## 감정 점수 기준
- 1-3점: 부정적 (슬픔, 분노, 불안, 스트레스)
- 4-6점: 중립적 (평범, 무난, 일상적)
- 7-10점: 긍정적 (기쁨, 행복, 만족, 설렘)

반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트 없이 JSON만 반환하세요:

{
  "average_score": 7.5,
  "evaluation": "positive",
  "daily_analysis": [
    {
      "date": "2026-01-05",
      "score": 8,
      "sentiment": "긍정적",
      "key_themes": ["운동", "새로운 시작"],
      "diary_content": "일기 내용 요약 (100자 이내)"
    }
  ],
  "patterns": [
    {
      "type": "activity",
      "value": "운동",
      "correlation": "positive",
      "frequency": 3,
      "average_score": 8.0
    }
  ],
  "feedback": [
    "이번 주는 전반적으로 긍정적이었습니다.",
    "운동한 날 기분이 좋았네요. 계속 유지하세요!",
    "# 📊 주간 리포트\\n\\n상세한 분석 내용..."
  ]
}
"""
    
    def analyze_sentiment(
        self,
        entries: List[Dict[str, Any]],
        nickname: str
    ) -> SentimentAnalysis:
        """
        일기 항목들의 감정을 분석합니다.
        
        Args:
            entries: 일기 항목 목록
            nickname: 작성자 닉네임
            
        Returns:
            감정 분석 결과 (SentimentAnalysis)
        """
        # 일기 내용 포맷팅
        diary_texts = []
        for entry in entries:
            record_date = entry.get("record_date", "")
            if isinstance(record_date, date):
                record_date = record_date.isoformat()
            content = entry.get("content", "")
            diary_texts.append(f"[{record_date}] {content}")
        
        prompt = f"""
작성자: {nickname}

다음 일기들을 분석해주세요:

{chr(10).join(diary_texts)}

JSON 형식으로 분석 결과를 반환해주세요.
"""
        
        logger.info(f"Strands Agent 분석 시작: {nickname}")
        
        try:
            # Agent 호출
            response = self.agent(prompt)
            logger.info(f"Strands Agent 분석 완료: {nickname}")
            
            # 응답 파싱
            return self._parse_response(str(response), entries)
            
        except Exception as e:
            logger.error(f"Strands Agent 분석 실패: {e}")
            raise StrandsServiceError(f"감정 분석 실패: {e}")
    
    def _parse_response(
        self,
        response: str,
        entries: List[Dict[str, Any]]
    ) -> SentimentAnalysis:
        """Agent 응답을 SentimentAnalysis로 파싱합니다."""
        
        # JSON 추출
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                data = json.loads(json_match.group())
                
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
                
            except json.JSONDecodeError as e:
                logger.warning(f"JSON 파싱 실패: {e}")
        
        # 파싱 실패 시 기본값 반환
        daily_scores = []
        for entry in entries:
            record_date = entry.get("record_date", "")
            if isinstance(record_date, date):
                record_date = record_date.isoformat()
            daily_scores.append(DailyScore(
                date=record_date,
                score=5.0,
                sentiment="분석 완료",
                key_themes=entry.get("tags", []) or []
            ))
        
        return SentimentAnalysis(
            daily_scores=daily_scores,
            positive_patterns=[],
            negative_patterns=[],
            recommendations=[response] if response else []
        )


@lru_cache()
def get_strands_service() -> StrandsAgentService:
    """Strands 서비스 싱글톤 인스턴스 반환"""
    return StrandsAgentService()
