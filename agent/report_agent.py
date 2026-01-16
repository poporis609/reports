# agent/report_agent.py
"""
Strands Agent - 주간 리포트 분석 Agent
"""
import sys
import os

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strands import Agent
from strands.models import BedrockModel
from agent.tools import (
    get_user_info,
    get_diary_entries,
    get_report_list,
    get_report_detail,
    save_report_to_db
)

# Claude Sonnet 4.5 모델 설정 (Bedrock) - inference profile 사용
model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    region_name="us-east-1"
)

# System Prompt
SYSTEM_PROMPT = """
당신은 사용자의 주간 감정 분석 리포트를 생성하는 전문 AI 상담사입니다.

## 역할
1. 사용자의 일기를 분석하여 감정 상태를 파악합니다
2. 일별 감정 점수(1-10)를 산출합니다
3. 긍정/부정 패턴을 발견합니다
4. 따뜻하고 공감적인 피드백을 제공합니다
5. 실천 가능한 개선 제안을 합니다

## 분석 프로세스
1. get_user_info로 사용자 정보 확인
2. get_diary_entries로 일기 데이터 수집
3. 각 일기의 감정을 분석하고 점수 산출
4. 패턴 발견 및 피드백 생성
5. save_report_to_db로 결과 저장

## 감정 점수 기준
- 1-3점: 부정적 (슬픔, 분노, 불안, 스트레스)
- 4-6점: 중립적 (평범, 무난, 일상적)
- 7-10점: 긍정적 (기쁨, 행복, 만족, 설렘)

## 출력 형식
리포트는 다음 구조로 생성합니다:
- average_score: 주간 평균 점수 (소수점 1자리)
- evaluation: "positive" (평균 5점 이상) 또는 "negative" (평균 5점 미만)
- daily_analysis: 일별 분석 배열
  - date: 날짜 (YYYY-MM-DD)
  - score: 감정 점수 (1-10)
  - sentiment: 감정 상태 설명
  - key_themes: 주요 테마 배열
  - diary_content: 일기 내용 요약 (100자 이내)
- patterns: 발견된 패턴 배열
  - type: 패턴 유형 (activity, time, social 등)
  - value: 패턴 값
  - correlation: "positive" 또는 "negative"
  - frequency: 빈도
  - average_score: 해당 패턴의 평균 점수
- feedback: 피드백 및 조언 배열 (3-5개)

## 대화 스타일
- 친근하고 따뜻한 톤
- 사용자의 감정에 공감
- 구체적이고 실천 가능한 조언
- 긍정적이고 격려하는 메시지
"""

# Agent 생성
report_agent = Agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    tools=[
        get_user_info,
        get_diary_entries,
        get_report_list,
        get_report_detail,
        save_report_to_db
    ]
)


def create_weekly_report(user_id: str, start_date: str, end_date: str) -> str:
    """
    주간 리포트를 생성합니다.
    
    Args:
        user_id: 사용자 ID
        start_date: 시작일 (YYYY-MM-DD)
        end_date: 종료일 (YYYY-MM-DD)
    
    Returns:
        생성된 리포트 정보
    """
    prompt = f"""
사용자 ID: {user_id}
분석 기간: {start_date} ~ {end_date}

위 사용자의 주간 감정 분석 리포트를 생성해주세요.

1. 먼저 get_user_info로 사용자 정보를 확인하세요
2. get_diary_entries로 해당 기간의 일기를 가져오세요
3. 각 일기를 분석하여 감정 점수와 패턴을 파악하세요
4. 분석 결과를 save_report_to_db로 저장하세요
5. 최종 리포트 요약을 반환하세요
"""
    
    response = report_agent(prompt)
    return str(response)


def chat_about_report(user_id: str, message: str) -> str:
    """
    리포트에 대해 대화합니다.
    
    Args:
        user_id: 사용자 ID
        message: 사용자 메시지
    
    Returns:
        Agent 응답
    """
    prompt = f"""
사용자 ID: {user_id}
사용자 메시지: {message}

사용자의 질문에 답변해주세요. 필요하면 도구를 사용하세요.
"""
    
    response = report_agent(prompt)
    return str(response)


# 테스트
if __name__ == "__main__":
    # 리포트 생성 테스트
    result = create_weekly_report(
        user_id="44681408-c0b1-70f3-2d06-2a725f290f8b",
        start_date="2026-01-05",
        end_date="2026-01-11"
    )
    print(result)
