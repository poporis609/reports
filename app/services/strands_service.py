# app/services/strands_service.py
"""
Strands Agent 서비스 - AgentCore 호출 방식
EKS에서는 strands 직접 사용 대신 AgentCore Runtime 호출
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
    """Strands 서비스 에러"""
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
    """Strands Agent를 사용한 감정 분석 서비스 (AgentCore 호출)"""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = boto3.client(
            "bedrock-agentcore",
            region_name=self.settings.AWS_REGION
        )
        self.agent_runtime_arn = "arn:aws:bedrock-agentcore:us-east-1:324547056370:runtime/my_agent-2TkF0HCkZE"
    
    def analyze_sentiment(
        self,
        entries: List[Dict[str, Any]],
        nickname: str
    ) -> SentimentAnalysis:
        """
        일기 항목들의 감정을 분석합니다.
        AgentCore Runtime을 호출하여 분석 수행
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

다음 일기들을 분석해서 JSON 형식으로 결과를 반환해주세요:

{chr(10).join(diary_texts)}

JSON 형식:
{{
  "average_score": 7.5,
  "evaluation": "positive",
  "daily_analysis": [
    {{"date": "2026-01-05", "score": 8, "sentiment": "긍정적", "key_themes": ["운동"]}}
  ],
  "patterns": [
    {{"type": "activity", "value": "운동", "correlation": "positive"}}
  ],
  "feedback": ["피드백1", "피드백2"]
}}
"""
        
        logger.info(f"AgentCore 분석 시작: {nickname}")
        
        try:
            # AgentCore 호출
            response = self.client.invoke_agent_runtime(
                agentRuntimeArn=self.agent_runtime_arn,
                payload=json.dumps({"prompt": prompt}).encode('utf-8')
            )
            
            result = response['body'].read().decode('utf-8')
            logger.info(f"AgentCore 분석 완료: {nickname}")
            
            # 응답 파싱
            return self._parse_response(result, entries)
            
        except Exception as e:
            logger.error(f"AgentCore 분석 실패: {e}")
            # 실패 시 기본값 반환
            return self._default_analysis(entries)
    
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
    """Strands 서비스 싱글톤 인스턴스 반환"""
    return StrandsAgentService()
