"""
주간 리포트 스케줄러 Lambda 함수
매주 월요일 00:00(KST)에 EventBridge에 의해 트리거됩니다.
"""
import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 한국 시간대 (UTC+9)
KST = timezone(timedelta(hours=9))

API_ENDPOINT = os.environ.get("API_ENDPOINT", "https://api.aws11.shop")


def get_previous_week_range() -> tuple:
    """지난 주의 시작일(월요일)과 종료일(일요일)을 한국 시간 기준으로 반환합니다."""
    today = datetime.now(KST).date()
    days_since_monday = today.weekday()
    this_monday = today - timedelta(days=days_since_monday)
    last_monday = this_monday - timedelta(days=7)
    last_sunday = last_monday + timedelta(days=6)
    return last_monday, last_sunday


def get_users_with_entries(week_start, week_end) -> list:
    """QueryDatabase Lambda를 통해 해당 기간에 일기가 있는 유저 목록 조회"""
    import boto3
    
    query = f"""
        SELECT DISTINCT u.user_id, u.email, u.nickname
        FROM users u
        INNER JOIN history h ON u.user_id = h.user_id
        WHERE h.record_date >= '{week_start}' AND h.record_date <= '{week_end}'
        AND u.deleted_at IS NULL
    """
    
    client = boto3.client('lambda', region_name='ap-northeast-2')
    response = client.invoke(
        FunctionName='QueryDatabase',
        InvocationType='RequestResponse',
        Payload=json.dumps({"query": query})
    )
    
    result = json.loads(response['Payload'].read().decode('utf-8'))
    body = json.loads(result.get('body', '{}'))
    
    if body.get('success'):
        return body.get('data', [])
    return []


def check_report_exists(user_id: str, week_start, week_end) -> bool:
    """해당 주에 이미 리포트가 존재하는지 확인"""
    import boto3
    
    query = f"""
        SELECT 1 FROM weekly_reports
        WHERE user_id = '{user_id}' AND week_start = '{week_start}' AND week_end = '{week_end}'
        LIMIT 1
    """
    
    client = boto3.client('lambda', region_name='ap-northeast-2')
    response = client.invoke(
        FunctionName='QueryDatabase',
        InvocationType='RequestResponse',
        Payload=json.dumps({"query": query})
    )
    
    result = json.loads(response['Payload'].read().decode('utf-8'))
    body = json.loads(result.get('body', '{}'))
    
    return body.get('count', 0) > 0


def invoke_report_generation(user_id: str, week_start, week_end) -> dict:
    """리포트 생성 API 호출"""
    url = f"{API_ENDPOINT}/report/create"
    data = json.dumps({
        "user_id": user_id,
        "start_date": str(week_start),
        "end_date": str(week_end)
    }).encode('utf-8')
    
    try:
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method='POST')
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            return {"success": True, "user_id": user_id, "report_id": result.get("report_id")}
    except Exception as e:
        return {"success": False, "user_id": user_id, "error": str(e)}


def lambda_handler(event, context):
    logger.info(f"주간 리포트 스케줄러 시작: {event}")
    
    week_start, week_end = get_previous_week_range()
    logger.info(f"분석 기간: {week_start} ~ {week_end}")
    
    results = {"total_users": 0, "success_count": 0, "skip_count": 0, "error_count": 0, "errors": []}
    
    try:
        users = get_users_with_entries(week_start, week_end)
        results["total_users"] = len(users)
        logger.info(f"적격 사용자 수: {len(users)}")
        
        for user in users:
            user_id = user["user_id"]
            nickname = user.get("nickname", "Unknown")
            
            try:
                if check_report_exists(user_id, week_start, week_end):
                    logger.info(f"사용자 {nickname}: 이미 리포트 존재, 건너뜀")
                    results["skip_count"] += 1
                    continue
                
                result = invoke_report_generation(user_id, week_start, week_end)
                
                if result.get("success"):
                    logger.info(f"사용자 {nickname}: 리포트 생성 요청 성공")
                    results["success_count"] += 1
                else:
                    logger.error(f"사용자 {nickname}: 리포트 생성 실패 - {result.get('error')}")
                    results["error_count"] += 1
                    results["errors"].append({"user_id": user_id, "error": result.get("error")})
                    
            except Exception as e:
                logger.error(f"사용자 {nickname}: 처리 중 오류 - {e}")
                results["error_count"] += 1
                results["errors"].append({"user_id": user_id, "error": str(e)})
                
    except Exception as e:
        logger.error(f"스케줄러 실행 중 오류: {e}")
        results["errors"].append({"global_error": str(e)})
    
    logger.info(f"스케줄러 완료: {json.dumps(results, ensure_ascii=False)}")
    
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "주간 리포트 스케줄러 실행 완료",
            "week_period": {"start": str(week_start), "end": str(week_end)},
            "results": results
        }, ensure_ascii=False)
    }
