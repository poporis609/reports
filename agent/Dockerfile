# agent/Dockerfile
# AWS Bedrock AgentCore Runtime 배포용

FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성
COPY agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드
COPY agent/ ./agent/
COPY app/ ./app/

# 환경 변수
ENV PYTHONPATH=/app
ENV AWS_REGION=us-east-1

# AgentCore Runtime 포트
EXPOSE 8080

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/ping || exit 1

# 실행
CMD ["python", "-m", "agent.agentcore_handler"]
