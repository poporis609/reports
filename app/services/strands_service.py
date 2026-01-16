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
- 구체적인 상황이나 활동을 언급하세요 (예: "금요일에 친구들과의 저녁 모임이...")
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
    "{nickname}님, 새 프로젝트 시작이 설레면서도 긴장되셨군요. 팀 분위기가 좋다니 좋은 출발입니다!",
    "금요일 친구들과의 저녁 모임에서 행복한 시간을 보내셨네요. 이런 사회적 연결이 정서적 안정에 큰 도움이 됩니다.",
    "야근으로 피곤하셨지만 맛있는 야식으로 스스로를 위로하신 점이 좋습니다. 자기 돌봄을 잘 하고 계세요."
  ]
}}
```
"""
        
        print(f"AgentCore 분석 시작: {nickname}")
        
        try:
            # AgentCore 호출
            print(f"AgentCore ARN: {self.agent_runtime_arn}")
            response = self.client.invoke_agent_runtime(
                agentRuntimeArn=self.agent_runtime_arn,
                payload=json.dumps({"prompt": prompt}).encode('utf-8')
            )
            
            print(f"AgentCore 응답 키: {list(response.keys())}")
            
            # 응답 파싱 - 다양한 형식 지원
            if 'response' in response:
                result = response['response']
                # StreamingBody 처리
                if hasattr(result, 'read'):
                    result = result.read().decode('utf-8')
                elif isinstance(result, bytes):
                    result = result.decode('utf-8')
            elif 'body' in response:
                result = response['body'].read().decode('utf-8')
            elif 'output' in response:
                result = response['output']
            elif 'result' in response:
                result = response['result']
            else:
                # 전체 응답을 문자열로 변환
                result = json.dumps(response, default=str)
            
            print(f"AgentCore 분석 완료: {nickname}, 응답 길이: {len(result)}")
            print(f"AgentCore 응답 미리보기: {result[:500]}")
            
            # 응답 파싱
            return self._parse_response(result, entries)
            
        except Exception as e:
            print(f"AgentCore 분석 실패: {e}")
            import traceback
            traceback.print_exc()
            # 실패 시 기본값 반환
            return self._default_analysis(entries)
    
    def _parse_response(
        self,
        response: str,
        entries: List[Dict[str, Any]]
    ) -> SentimentAnalysis:
        """Agent 응답을 SentimentAnalysis로 파싱합니다."""
        
        print(f"파싱 시작, 응답 타입: {type(response)}")
        
        try:
            # 먼저 전체 응답을 JSON으로 파싱 시도
            outer_data = json.loads(response)
            
            # result 키가 있으면 그 안의 내용에서 JSON 추출
            if "result" in outer_data:
                inner_content = outer_data["result"]
                print(f"result 키 발견, 내부 컨텐츠 길이: {len(inner_content)}")
                
                # 내부 컨텐츠에서 JSON 블록 추출
                json_match = re.search(r'```json\s*([\s\S]*?)\s*```', inner_content)
                if json_match:
                    json_str = json_match.group(1)
                    print(f"JSON 블록 발견: {json_str[:200]}")
                    data = json.loads(json_str)
                else:
                    # ```json 없이 직접 JSON 객체 찾기
                    json_match = re.search(r'\{[^{}]*"daily_analysis"[^{}]*\[[\s\S]*?\]\s*\}', inner_content)
                    if json_match:
                        data = json.loads(json_match.group())
                    else:
                        print("JSON 블록을 찾을 수 없음")
                        return self._default_analysis(entries)
            else:
                # result 키가 없으면 직접 데이터로 사용
                data = outer_data
                
        except json.JSONDecodeError:
            # 전체가 JSON이 아니면 기존 방식으로 추출
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                except json.JSONDecodeError as e:
                    print(f"JSON 파싱 실패: {e}")
                    return self._default_analysis(entries)
            else:
                return self._default_analysis(entries)
        
        print(f"파싱된 데이터 키: {list(data.keys())}")
        
        # daily_scores 생성
        daily_scores = []
        for item in data.get("daily_analysis", []):
            daily_scores.append(DailyScore(
                date=item.get("date", ""),
                score=float(item.get("score", 5)),
                sentiment=item.get("sentiment", "분석 완료"),
                key_themes=item.get("key_themes", [])
            ))
        
        print(f"daily_scores 개수: {len(daily_scores)}")
        
        # 패턴 추출
        positive_patterns = []
        negative_patterns = []
        for pattern in data.get("patterns", []):
            pattern_str = f"{pattern.get('value', '')} ({pattern.get('type', '')})"
            if pattern.get("correlation") == "positive":
                positive_patterns.append(pattern_str)
            else:
                negative_patterns.append(pattern_str)
        
        feedback = data.get("feedback", [])
        print(f"피드백 개수: {len(feedback)}")
        
        return SentimentAnalysis(
            daily_scores=daily_scores,
            positive_patterns=positive_patterns,
            negative_patterns=negative_patterns,
            recommendations=feedback
        )
    
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
