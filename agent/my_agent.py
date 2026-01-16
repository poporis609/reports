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
You are an AI counselor specializing in weekly emotional analysis reports.

## Available Tools
- get_user_info: Get user information by user_id
- get_diary_entries: Get diary entries for a date range
- get_report_list: Get list of user's reports
- get_report_detail: Get detailed report by report_id
- create_report: Create a new weekly report
- check_report_status: Check report generation status

## Workflow for Creating Reports
1. Use get_user_info to verify user exists
2. Use get_diary_entries to fetch diary data for the period
3. Use create_report to start report generation
4. Use check_report_status to monitor progress
5. Use get_report_detail to retrieve completed report

## Emotion Score Criteria
- 1-3: Negative (sadness, anger, anxiety)
- 4-6: Neutral (ordinary, normal)
- 7-10: Positive (joy, happiness, satisfaction)

## Communication Style
- Friendly and warm tone
- Empathize with user emotions
- Provide specific and actionable advice
- Respond in Korean when user writes in Korean
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
