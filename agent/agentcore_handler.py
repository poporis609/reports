# agent/agentcore_handler.py
"""
AWS Bedrock AgentCore Runtime 배포용 핸들러
AgentCore Runtime Python SDK 사용
"""
import sys
import os
import logging

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bedrock_agentcore_runtime import BedrockAgentCoreApp
from strands import Agent
from strands.models import BedrockModel

from agent.tools import (
    get_user_info,
    get_diary_entries,
    get_report_list,
    get_report_detail,
    save_report_to_db
)

logger = logging.getLogger(__name__)

# 1. AgentCore App 초기화
app = BedrockAgentCoreApp()

# 2. Claude Sonnet 4.5 모델 (inference profile)
model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    region_name=os.environ.get("AWS_REGION", "us-east-1")
)

# 3. System Prompt
SYSTEM_PROMPT = """
당신은 사용자의 주간 감정 분석 리포트를 생성하는 전문 AI 상담사입니다.

## 역할
1. 사용자의 일기를 분석하여 감정 상태를 파악합니다
2. 일별 감정 점수(1-10)를 산출합니다
3. 긍정/부정 패턴을 발견합니다
4. 따뜻하고 공감적인 피드백을 제공합니다

## 사용 가능한 도구
- get_user_info: 사용자 정보 조회
- get_diary_entries: 일기 항목 조회
- get_report_list: 리포트 목록 조회
- get_report_detail: 리포트 상세 조회
- save_report_to_db: 리포트 저장

## 감정 점수 기준
- 1-3점: 부정적 (슬픔, 분노, 불안)
- 4-6점: 중립적 (평범, 무난)
- 7-10점: 긍정적 (기쁨, 행복, 만족)

## 대화 스타일
- 친근하고 따뜻한 톤
- 사용자의 감정에 공감
- 구체적이고 실천 가능한 조언
"""

# 4. Strands Agent 생성
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


# 5. AgentCore 핸들러 데코레이터
@app.handler
def handle_request(event: dict) -> dict:
    """
    AgentCore Runtime 요청 핸들러
    
    Args:
        event: AgentCore 요청
            - prompt: 사용자 입력
            - user_id: 사용자 ID (optional)
    
    Returns:
        AgentCore 응답
    """
    try:
        prompt = event.get("prompt", "")
        user_id = event.get("user_id", "")
        
        logger.info(f"AgentCore 요청: user={user_id}")
        
        # user_id가 있으면 프롬프트에 추가
        if user_id:
            full_prompt = f"[사용자 ID: {user_id}]\n\n{prompt}"
        else:
            full_prompt = prompt
        
        # Agent 호출
        response = report_agent(full_prompt)
        
        logger.info(f"AgentCore 응답 완료")
        
        return {
            "message": str(response),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"AgentCore 에러: {e}")
        return {
            "message": f"오류가 발생했습니다: {str(e)}",
            "status": "error"
        }


# 로컬 테스트용
if __name__ == "__main__":
    # 로컬 서버 실행
    app.run(host="0.0.0.0", port=8080)
