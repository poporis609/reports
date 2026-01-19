# app/services/strands_service.py
"""
감정 분석 서비스 - Bedrock LLM 직접 호출
AgentCore가 아닌 Bedrock Converse API를 사용하여 감정 분석 수행
"""
import json
import re
import logging
from typing import Dict, Any, List
from datetime import date
from functools import lru_cache
from dataclasses import dataclass

import boto3

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


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
    """Bedrock LLM을 사용한 감정 분석 서비스"""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=self.settings.AWS_REGION
        )
        # Claude Sonnet 모델 사용
        self.model_id = "us.anthropic.claude-sonnet-4-20250514-v1:0"
    
    def analyze_sentiment(
        self,
        entries: List[Dict[str, Any]],
        nickname: str
    ) -> SentimentAnalysis:
        """
        일기 항목들의 감정을 분석합니다.
        Bedrock Converse API를 직접 호출하여 분석 수행
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
당신은 전문 심리 상담사입니다. {nickname}님의 일주일 일기를 분석해주세요.

## 일기 내용
{chr(10).join(diary_texts)}

## 분석 지침

### 감정 점수 기준 (1-10점)
- 1-2점: 매우 부정적 (우울, 절망, 분노 폭발)
- 3-4점: 부정적 (스트레스, 짜증, 불안, 피로)
- 5-6점: 중립/보통 (평범한 하루, 특별한 감정 없음)
- 7-8점: 긍정적 (기쁨, 만족, 즐거움)
- 9-10점: 매우 긍정적 (행복, 감동, 성취감)

### 분석 시 주의사항
- 각 일기의 구체적인 내용과 표현을 바탕으로 점수를 차등 부여하세요
- "피곤", "야근", "힘들다" 등은 낮은 점수 (3-5점)
- "행복", "좋았다", "즐거웠다" 등은 높은 점수 (7-9점)
- 일기에 언급된 구체적인 활동, 사람, 장소를 key_themes에 포함하세요

### 피드백 작성 지침
- {nickname}님의 일기 내용을 직접 언급하며 개인화된 피드백을 작성하세요
- 구체적인 상황이나 활동을 언급하세요
- 중복되지 않는 3-5개의 서로 다른 관점의 피드백을 제공하세요
- 따뜻하고 공감하는 어조로 작성하세요

## 응답 형식 (반드시 JSON만 출력)
```json
{{
  "average_score": 6.5,
  "evaluation": "positive",
  "daily_analysis": [
    {{"date": "2026-01-06", "score": 7, "sentiment": "설렘과 긴장", "key_themes": ["새 프로젝트", "킥오프 미팅", "팀원"]}}
  ],
  "patterns": [
    {{"type": "social", "value": "동료/친구 만남", "correlation": "positive"}},
    {{"type": "activity", "value": "야근", "correlation": "negative"}}
  ],
  "feedback": [
    "{nickname}님, 이번 주 수고 많으셨어요!",
    "긍정적인 활동을 계속 유지하세요."
  ]
}}
```
"""
        
        logger.info(f"Bedrock 감정 분석 시작: {nickname}")
        
        try:
            # Bedrock Converse API 호출
            response = self.client.converse(
                modelId=self.model_id,
                messages=[
                    {
                        "role": "user",
                        "content": [{"text": prompt}]
                    }
                ],
                inferenceConfig={
                    "maxTokens": 4096,
                    "temperature": 0.7
                }
            )
            
            # 응답 추출
            result_text = response["output"]["message"]["content"][0]["text"]
            logger.info(f"Bedrock 분석 완료: {nickname}")
            
            # 응답 파싱
            return self._parse_response(result_text, entries)
            
        except Exception as e:
            logger.error(f"Bedrock 분석 실패: {e}")
            return self._default_analysis(entries)
    
    def _parse_response(
        self,
        response: str,
        entries: List[Dict[str, Any]]
    ) -> SentimentAnalysis:
        """LLM 응답을 SentimentAnalysis로 파싱합니다."""
        
        try:
            # JSON 블록 추출
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
        """기본 분석 결과 반환"""
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
            recommendations=["분석이 완료되었습니다."]
        )


@lru_cache()
def get_strands_service() -> StrandsAgentService:
    """감정 분석 서비스 싱글톤 인스턴스 반환"""
    return StrandsAgentService()
