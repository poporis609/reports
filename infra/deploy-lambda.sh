#!/bin/bash
# Lambda 함수 배포 스크립트

set -e

FUNCTION_NAME="weekly-report-scheduler"
REGION="us-east-1"
RUNTIME="python3.11"
HANDLER="lambda_function.lambda_handler"
TIMEOUT=300
MEMORY=512

# Lambda 배포 패키지 생성
echo "Creating deployment package..."
cd lambda/weekly_report_scheduler
pip install -r requirements.txt -t .
zip -r ../../lambda-package.zip .
cd ../..

# Lambda 함수 생성 또는 업데이트
echo "Deploying Lambda function..."
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION 2>/dev/null; then
    echo "Updating existing function..."
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://lambda-package.zip \
        --region $REGION
else
    echo "Creating new function..."
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime $RUNTIME \
        --handler $HANDLER \
        --timeout $TIMEOUT \
        --memory-size $MEMORY \
        --zip-file fileb://lambda-package.zip \
        --role arn:aws:iam::ACCOUNT_ID:role/weekly-report-lambda-role \
        --region $REGION \
        --environment "Variables={DB_HOST=fproject-dev-postgres.c9eksq6cmh3c.us-east-1.rds.amazonaws.com,DB_PORT=5432,DB_NAME=fproject_db,DB_USER=fproject_user,DB_SECRET_NAME=library-api/db-password,AWS_REGION=us-east-1}"
fi

# EventBridge 규칙 생성
echo "Creating EventBridge rule..."
aws events put-rule \
    --name weekly-report-scheduler \
    --schedule-expression "cron(0 0 ? * SUN *)" \
    --state ENABLED \
    --region $REGION

# Lambda 권한 추가
echo "Adding Lambda permission for EventBridge..."
aws lambda add-permission \
    --function-name $FUNCTION_NAME \
    --statement-id eventbridge-weekly-report \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn arn:aws:events:$REGION:ACCOUNT_ID:rule/weekly-report-scheduler \
    --region $REGION 2>/dev/null || true

# EventBridge 타겟 설정
echo "Setting EventBridge target..."
aws events put-targets \
    --rule weekly-report-scheduler \
    --targets "Id"="weekly-report-lambda","Arn"="arn:aws:lambda:$REGION:ACCOUNT_ID:function:$FUNCTION_NAME" \
    --region $REGION

# 정리
rm -f lambda-package.zip

echo "Deployment complete!"
