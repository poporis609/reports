"""
Bedrock 서비스 - AI 감정 분석
"""
import json
import boto3
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache

from app.config.settings import get_settings


@dataclass
class DailyScore:
    """일별 감정 점수"""
    date: str
    score: float
    sentiment: str
    key_themes: List[str] = field(default_factory=list)


@dataclass
class SentimentAnalysis:
    """감정 분석 결과"""
    daily_scores: List[DailyScore]
    positive_patterns: List[str] = field(default_factory=list)
    negative_patterns: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class BedrockServiceError(Exception):
    """Bedrock 서비스 에러"""
    pass


class BedrockTimeoutError(BedrockServiceError):
    """Bedrock 타임아웃 에러"""
    pass


class BedrockService:
    """AWS Bedrock Flow를 사용한 감정 분석 서비스"""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = boto3.client(
            "bedrock-agent-runtime",
            region_name=self.settings.AWS_REGION
        )
        self.flow_id = self.settings.BEDROCK_FLOW_ID
        self.flow_alias_id = self.settings.BEDROCK_FLOW_ALIAS_ID
        self.timeout = self.settings.BEDROCK_TIMEOUT
    
    def format_entries_for_bedrock(
        self,
        entries: List[Dict[str, Any]],
        nickname: str
    ) -> Dict[str, Any]:
        """
        일기 항목을 Bedrock 입력 형식으로 변환합니다.
        
        Args:
            entries: 일기 항목 목록
            nickname: 작성자 닉네임
            
        Returns:
            Bedrock 입력 형식의 딕셔너리
        """
        documents = []
        for entry in entries:
            doc = {
                "diaryContent": entry.get("content", ""),
                "createdDate": entry.get("record_date", ""),
                "authorNickname": nickname,
            }
            # 태그가 있으면 추가
            if entry.get("tags"):
                doc["tags"] = entry.get("tags")
            documents.append(doc)
        
        return {"documents": documents}
    
    def _invoke_flow_with_retry(
        self,
        input_data: Dict[str, Any],
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Bedrock Flow를 재시도 로직과 함께 호출합니다.
        
        Args:
            input_data: 입력 데이터
            max_retries: 최대 재시도 횟수
            
        Returns:
            Flow 응답
        """
        retry_delays = [1, 2, 4]  # 지수 백오프
        last_error = None
        
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                
                response = self.client.invoke_flow(
                    flowIdentifier=self.flow_id,
                    flowAliasIdentifier=self.flow_alias_id,
                    inputs=[
                        {
                            "content": {
                                "document": input_data
                            },
                            "nodeName": "FlowInputNode",
                            "nodeOutputName": "document"
                        }
                    ]
                )
                
                # 타임아웃 체크
                elapsed = time.time() - start_time
                if elapsed > self.timeout:
                    raise BedrockTimeoutError(
                        f"Bedrock Flow 요청이 {self.timeout}초를 초과했습니다"
                    )
                
                # 응답 스트림 처리
                result = self._process_response_stream(response)
                return result
                
            except BedrockTimeoutError:
                raise
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    time.sleep(retry_delays[attempt])
                continue
        
        raise BedrockServiceError(f"Bedrock Flow 호출 실패: {last_error}")
    
    def _process_response_stream(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Bedrock Flow 응답 스트림을 처리합니다.
        
        Args:
            response: Flow 응답
            
        Returns:
            파싱된 결과
        """
        result = {}
        
        for event in response.get("responseStream", []):
            if "flowOutputEvent" in event:
                output = event["flowOutputEvent"]
                content = output.get("content", {})
                if "document" in content:
                    result = content["document"]
                    break
        
        return result
    
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
            감정 분석 결과
        """
        if not entries:
            raise BedrockServiceError("분석할 일기 항목이 없습니다")
        
        # 입력 데이터 포맷팅
        input_data = self.format_entries_for_bedrock(entries, nickname)
        
        # Bedrock Flow 호출
        result = self._invoke_flow_with_retry(input_data)
        
        # 결과 파싱
        return self._parse_analysis_result(result, entries)
    
    def _parse_analysis_result(
        self,
        result: Dict[str, Any],
        entries: List[Dict[str, Any]]
    ) -> SentimentAnalysis:
        """
        Bedrock 응답을 SentimentAnalysis로 파싱합니다.
        
        Args:
            result: Bedrock 응답
            entries: 원본 일기 항목
            
        Returns:
            파싱된 감정 분석 결과
        """
        daily_scores = []
        
        # 일별 점수 파싱
        raw_scores = result.get("dailyScores", [])
        for score_data in raw_scores:
            daily_scores.append(DailyScore(
                date=score_data.get("date", ""),
                score=float(score_data.get("score", 5.0)),
                sentiment=score_data.get("sentiment", "중립"),
                key_themes=score_data.get("keyThemes", [])
            ))
        
        # 일별 점수가 없으면 기본값 생성
        if not daily_scores:
            for entry in entries:
                record_date = entry.get("record_date", "")
                if isinstance(record_date, date):
                    record_date = record_date.isoformat()
                daily_scores.append(DailyScore(
                    date=record_date,
                    score=5.0,
                    sentiment="분석 중",
                    key_themes=entry.get("tags", []) or []
                ))
        
        # 주간 인사이트 파싱
        insights = result.get("weeklyInsights", {})
        
        return SentimentAnalysis(
            daily_scores=daily_scores,
            positive_patterns=insights.get("positivePatterns", []),
            negative_patterns=insights.get("negativePatterns", []),
            recommendations=insights.get("recommendations", [])
        )


@lru_cache()
def get_bedrock_service() -> BedrockService:
    """Bedrock 서비스 싱글톤 인스턴스 반환"""
    return BedrockService()
