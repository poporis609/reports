#!/bin/bash
# AWS Secrets Manager에 애플리케이션 설정이 있는지 확인하고 없으면 생성

set -e

AWS_REGION="us-east-1"
SECRET_NAME="weekly-report/app-config"

echo "Checking if secret exists..."

# Secret 존재 여부 확인
if aws secretsmanager describe-secret --secret-id "$SECRET_NAME" --region "$AWS_REGION" 2>/dev/null; then
    echo "✅ Secret '$SECRET_NAME' already exists"
    echo ""
    echo "Current secret value:"
    aws secretsmanager get-secret-value --secret-id "$SECRET_NAME" --region "$AWS_REGION" --query SecretString --output text | jq .
else
    echo "❌ Secret '$SECRET_NAME' does not exist"
    echo ""
    echo "Please provide the following values:"
    read -p "BEDROCK_FLOW_ID: " BEDROCK_FLOW_ID
    read -p "BEDROCK_FLOW_ALIAS_ID: " BEDROCK_FLOW_ALIAS_ID
    read -p "COGNITO_USER_POOL_ID: " COGNITO_USER_POOL_ID
    read -p "COGNITO_CLIENT_ID: " COGNITO_CLIENT_ID
    
    echo ""
    echo "Creating secret..."
    
    aws secretsmanager create-secret \
        --name "$SECRET_NAME" \
        --description "Weekly Report Service Application Configuration" \
        --secret-string "{
            \"BEDROCK_FLOW_ID\": \"$BEDROCK_FLOW_ID\",
            \"BEDROCK_FLOW_ALIAS_ID\": \"$BEDROCK_FLOW_ALIAS_ID\",
            \"COGNITO_USER_POOL_ID\": \"$COGNITO_USER_POOL_ID\",
            \"COGNITO_CLIENT_ID\": \"$COGNITO_CLIENT_ID\"
        }" \
        --region "$AWS_REGION"
    
    echo "✅ Secret created successfully!"
fi
