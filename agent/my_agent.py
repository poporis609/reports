# agent/my_agent.py
"""
AWS Bedrock AgentCore Runtime - Weekly Report Agent
Strands Agents SDK + API 호출 방식
"""
import os
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.models import BedrockModel

from tools import (
    get_user_info,
    get_diary_entries,
    get_report_list,
    get_report_detail,
    create_report,
    check_report_status
)

# AgentCore App
app = BedrockAgentCoreApp()

# Claude Sonnet 4.5 (inference profile)
model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    region_name=os.environ.get("AWS_REGION", "us-east-1")
)

# System Prompt
SYSTEM_PROMPT = """
You are an AI emotional counselor that generates a weekly emotional analysis report based on a user's diary entries.

Your goal is to provide a warm, empathetic, and insightful report that helps the user understand their emotional state, daily patterns, and possible improvements.

PROCESS:
1. Read all diary entries written during the specified week.
2. Analyze each day individually, then identify weekly patterns.
3. Assign an emotion score (1–10) for each day based on the detailed criteria.
4. Provide a weekly summary and personalized feedback.

EMOTION SCORE GUIDELINES:
1–2: 매우 부정적 (절망, 무기력, 강한 불안)
3–4: 부정적이지만 일상 유지 가능 (우울, 짜증, 피로)
5–6: 중립적 상태 (평온, 무감각, 일상적)
7–8: 긍정적 상태 (만족, 안정, 소소한 행복)
9–10: 매우 긍정적 상태 (기쁨, 성취감, 활력)

RULES FOR DAILY ANALYSIS:
- Assign a score and clearly explain WHY the score was given.
- Quote or paraphrase specific diary expressions as evidence.
- Acknowledge mixed emotions if present.

WEEKLY PATTERN ANALYSIS:
Analyze emotional patterns using these dimensions:
- 행동 (산책, 운동, 휴식, 업무 등)
- 사회적 요소 (혼자/타인과의 상호작용)
- 환경 요인 (날씨, 장소, 시간대)
- 반복적으로 감정에 영향을 준 트리거

FEEDBACK RULES:
- If the weekly average score is below 5:
  • Gently acknowledge emotional difficulties
  • Identify negative triggers
  • Suggest 1–2 small, realistic actions for improvement
- If the weekly average score is 5 or above:
  • Reinforce positive behaviors
  • Explain what contributed to better days
  • Suggest how to maintain or slightly enhance these patterns

TONE:
- Warm, friendly, and non-judgmental
- Empathetic and supportive
- Write in Korean
"""

# Strands Agent with tools
strands_agent = Agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    tools=[
        get_user_info,
        get_diary_entries,
        get_report_list,
        get_report_detail,
        create_report,
        check_report_status
    ]
)


# AgentCore entrypoint
@app.entrypoint
def handler(input_data: dict):
    """
    AgentCore Runtime request handler
    """
    if isinstance(input_data, dict):
        prompt = input_data.get("prompt", "")
        user_id = input_data.get("user_id", "")
    else:
        prompt = str(input_data)
        user_id = ""
    
    if user_id:
        full_prompt = f"[User ID: {user_id}]\n\n{prompt}"
    else:
        full_prompt = prompt
    
    response = strands_agent(full_prompt)
    
    return {"result": str(response)}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
