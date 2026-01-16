# agent/deploy_agent.py
"""
AWS Bedrock AgentCore Runtime 배포 스크립트 (boto3)
"""
import boto3
import json
import os
import time

# 설정
AGENT_NAME = "weekly-report-agent"
REGION = "us-east-1"
ACCOUNT_ID = boto3.client("sts").get_caller_identity()["Account"]

# ECR 이미지 URI (먼저 빌드 & 푸시 필요)
ECR_IMAGE_URI = f"{ACCOUNT_ID}.dkr.ecr.{REGION}.amazonaws.com/{AGENT_NAME}:latest"

# IAM Role ARN (미리 생성 필요)
AGENT_ROLE_ARN = f"arn:aws:iam::{ACCOUNT_ID}:role/BedrockAgentCoreRole"


def create_agent_runtime():
    """AgentCore Runtime 생성"""
    client = boto3.client("bedrock-agent", region_name=REGION)
    
    try:
        response = client.create_agent_runtime(
            agentRuntimeName=AGENT_NAME,
            description="주간 감정 분석 리포트 생성 AI Agent",
            agentRuntimeArtifact={
                "containerConfiguration": {
                    "containerUri": ECR_IMAGE_URI
                }
            },
            roleArn=AGENT_ROLE_ARN,
            networkConfiguration={
                "networkMode": "PUBLIC"  # 또는 VPC 설정
            }
        )
        
        agent_runtime_id = response["agentRuntimeId"]
        print(f"✅ AgentCore Runtime 생성됨: {agent_runtime_id}")
        return agent_runtime_id
        
    except client.exceptions.ConflictException:
        print(f"⚠️ Agent '{AGENT_NAME}'가 이미 존재합니다.")
        # 기존 Agent 조회
        agents = client.list_agent_runtimes()
        for agent in agents.get("agentRuntimeSummaries", []):
            if agent["agentRuntimeName"] == AGENT_NAME:
                return agent["agentRuntimeId"]
        return None


def wait_for_agent_ready(agent_runtime_id: str, timeout: int = 300):
    """Agent가 준비될 때까지 대기"""
    client = boto3.client("bedrock-agent", region_name=REGION)
    
    print("⏳ Agent 준비 대기 중...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        response = client.get_agent_runtime(agentRuntimeId=agent_runtime_id)
        status = response["agentRuntimeStatus"]
        
        if status == "ACTIVE":
            print(f"✅ Agent 준비 완료!")
            return True
        elif status in ["FAILED", "DELETING"]:
            print(f"❌ Agent 상태: {status}")
            return False
        
        print(f"   상태: {status}...")
        time.sleep(10)
    
    print("❌ 타임아웃")
    return False


def invoke_agent(agent_runtime_id: str, prompt: str, user_id: str = None):
    """Agent 호출"""
    client = boto3.client("bedrock-agent-runtime", region_name=REGION)
    
    input_data = {"prompt": prompt}
    if user_id:
        input_data["user_id"] = user_id
    
    response = client.invoke_agent_runtime(
        agentRuntimeId=agent_runtime_id,
        input=json.dumps(input_data)
    )
    
    result = json.loads(response["output"].read())
    return result


if __name__ == "__main__":
    print("🚀 Weekly Report Agent 배포")
    print(f"   Region: {REGION}")
    print(f"   Account: {ACCOUNT_ID}")
    print("")
    
    # 1. Agent Runtime 생성
    agent_runtime_id = create_agent_runtime()
    
    if agent_runtime_id:
        # 2. 준비 대기
        if wait_for_agent_ready(agent_runtime_id):
            # 3. 테스트 호출
            print("\n🧪 테스트 호출...")
            result = invoke_agent(
                agent_runtime_id,
                "안녕하세요, 간단히 인사해주세요",
                user_id="test-user"
            )
            print(f"응답: {result}")
            
            print(f"\n📋 Agent Runtime ID: {agent_runtime_id}")
            print("이 ID를 app/config/settings.py에 설정하세요.")
