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
        self.flow_id = self.settings.get_bedrock_flow_id()
        self.flow_alias_id = self.settings.get_bedrock_flow_alias_id()
        self.timeout = self.settings.BEDROCK_TIMEOUT
    
    def format_entries_for_bedrock(
        self,
        entries: List[Dict[str, Any]],
        nickname: str
    ) -> str:
        """
        일기 항목을 Bedrock Flow 입력 형식(텍스트)으로 변환합니다.
        
        Args:
            entries: 일기 항목 목록
            nickname: 작성자 닉네임
            
        Returns:
            일기 내용을 합친 텍스트
        """
        diary_texts = []
        for entry in entries:
            record_date = entry.get("record_date", "")
            if isinstance(record_date, date):
                record_date = record_date.isoformat()
            
            content = entry.get("content", "")
            diary_texts.append(f"[{record_date}] {content}")
        
        # 일기 내용을 줄바꿈으로 연결
        return f"작성자: {nickname}\n\n" + "\n\n".join(diary_texts)
    
    def _invoke_flow_with_retry(
        self,
        input_text: str,
        max_retries: int = 3
    ) -> str:
        """
        Bedrock Flow를 재시도 로직과 함께 호출합니다.
        
        Args:
            input_text: 입력 텍스트
            max_retries: 최대 재시도 횟수
            
        Returns:
            Flow 응답 텍스트
        """
        retry_delays = [1, 2, 4]  # 지수 백오프
        last_error = None
        
        for attempt in range(max_retries):
            try:
                response = self.client.invoke_flow(
                    flowIdentifier=self.flow_id,
                    flowAliasIdentifier=self.flow_alias_id,
                    inputs=[
                        {
                            "content": {
                                "document": input_text
                            },
                            "nodeName": "FlowInputNode",
                            "nodeOutputName": "document"
                        }
                    ]
                )
                
                # 응답 스트림 처리
                result = self._process_response_stream(response)
                return result
                
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    time.sleep(retry_delays[attempt])
                continue
        
        raise BedrockServiceError(f"Bedrock Flow 호출 실패: {last_error}")
    
    def _process_response_stream(self, response: Dict[str, Any]) -> str:
        """
        Bedrock Flow 응답 스트림을 처리합니다.
        
        Args:
            response: Flow 응답
            
        Returns:
            응답 텍스트
        """
        result = ""
        
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
        
        # 입력 텍스트 포맷팅
        input_text = self.format_entries_for_bedrock(entries, nickname)
        
        # Bedrock Flow 호출
        result_text = self._invoke_flow_with_retry(input_text)
        
        # 결과 파싱 (텍스트 응답을 SentimentAnalysis로 변환)
        return self._parse_analysis_result(result_text, entries)
    
    def _parse_analysis_result(
        self,
        result_text: str,
        entries: List[Dict[str, Any]]
    ) -> SentimentAnalysis:
        """
        Bedrock 응답 텍스트를 SentimentAnalysis로 파싱합니다.
        
        Args:
            result_text: Bedrock 응답 텍스트
            entries: 원본 일기 항목
            
        Returns:
            파싱된 감정 분석 결과
        """
        daily_scores = []
        
        # Flow 응답은 텍스트이므로 일별 점수는 기본값 생성
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
        
        # Flow 응답 텍스트를 recommendations에 저장
        return SentimentAnalysis(
            daily_scores=daily_scores,
            positive_patterns=[],
            negative_patterns=[],
            recommendations=[result_text] if result_text else []
        )


@lru_cache()
def get_bedrock_service() -> BedrockService:
    """Bedrock 서비스 싱글톤 인스턴스 반환"""
    return BedrockService()
