#!/bin/bash
# AWS Secrets Manager에 애플리케이션 설정 저장
# 이 스크립트는 한 번만 실행하면 됩니다.

set -e

AWS_REGION="us-east-1"
SECRET_NAME="weekly-report/app-config"

echo "Creating secret in AWS Secrets Manager..."

# Secret 생성 (이미 존재하면 업데이트)
aws secretsmanager create-secret \
    --name "$SECRET_NAME" \
    --description "Weekly Report Service Application Configuration" \
    --secret-string '{
        "BEDROCK_FLOW_ID": "YOUR_BEDROCK_FLOW_ID",
        "BEDROCK_FLOW_ALIAS_ID": "YOUR_BEDROCK_FLOW_ALIAS_ID",
        "COGNITO_USER_POOL_ID": "YOUR_COGNITO_USER_POOL_ID",
        "COGNITO_CLIENT_ID": "YOUR_COGNITO_CLIENT_ID"
    }' \
    --region "$AWS_REGION" 2>/dev/null || \

# 이미 존재하면 업데이트
aws secretsmanager update-secret \
    --secret-id "$SECRET_NAME" \
    --secret-string '{
        "BEDROCK_FLOW_ID": "YOUR_BEDROCK_FLOW_ID",
        "BEDROCK_FLOW_ALIAS_ID": "YOUR_BEDROCK_FLOW_ALIAS_ID",
        "COGNITO_USER_POOL_ID": "YOUR_COGNITO_USER_POOL_ID",
        "COGNITO_CLIENT_ID": "YOUR_COGNITO_CLIENT_ID"
    }' \
    --region "$AWS_REGION"

echo "Secret created/updated successfully!"
echo ""
echo "Next steps:"
echo "1. Update the secret values in AWS Console or using AWS CLI"
echo "2. Update IAM policy to allow access to this secret"
echo "3. Update the application to read from this secret"
