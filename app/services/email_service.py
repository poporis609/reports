"""
이메일 서비스 - AWS SES를 통한 알림 발송
"""
import boto3
import time
import logging
from typing import Optional
from functools import lru_cache

from app.config.settings import get_settings
from app.services.report_service import WeeklyReportResult

logger = logging.getLogger(__name__)


class EmailServiceError(Exception):
    """이메일 서비스 에러"""
    pass


class EmailService:
    """AWS SES 이메일 서비스"""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = boto3.client(
            "ses",
            region_name=self.settings.AWS_REGION
        )
        self.sender_email = self.settings.SES_SENDER_EMAIL
        self.api_base_url = self.settings.API_BASE_URL
    
    def _create_report_email_html(self, report: WeeklyReportResult) -> str:
        """리포트 알림 이메일 HTML 생성"""
        evaluation_text = "긍정적" if report.evaluation == "positive" else "부정적"
        evaluation_emoji = "😊" if report.evaluation == "positive" else "😔"
        
        feedback_html = "".join([f"<li>{fb}</li>" for fb in report.feedback[:5]])
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>주간 감정 분석 완료</title>
    <style>
        body {{ font-family: 'Noto Sans KR', sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; text-align: center; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .score-box {{ background: white; padding: 20px; border-radius: 10px; text-align: center; margin: 20px 0; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .score {{ font-size: 48px; font-weight: bold; color: #667eea; }}
        .feedback {{ background: white; padding: 15px; border-radius: 10px; margin: 15px 0; }}
        .feedback ul {{ margin: 0; padding-left: 20px; }}
        .feedback li {{ margin: 10px 0; }}
        .button {{ display: inline-block; background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
        .footer {{ text-align: center; color: #888; font-size: 12px; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{evaluation_emoji} 주간 감정 분석 완료</h1>
            <p>{report.nickname}님의 {report.week_start} ~ {report.week_end} 분석 결과</p>
        </div>
        <div class="content">
            <div class="score-box">
                <p>이번 주 평균 감정 점수</p>
                <div class="score">{report.average_score}/10</div>
                <p>전반적으로 <strong>{evaluation_text}</strong>인 한 주였습니다</p>
            </div>
            
            <div class="feedback">
                <h3>📝 주요 피드백</h3>
                <ul>
                    {feedback_html}
                </ul>
            </div>
            
            <div style="text-align: center;">
                <a href="{self.api_base_url}/report/{report.user_id}" class="button">
                    전체 리포트 보기
                </a>
            </div>
        </div>
        <div class="footer">
            <p>이 이메일은 주간 감정 분석 서비스에서 자동으로 발송되었습니다.</p>
            <p>© 2026 Weekly Report Service</p>
        </div>
    </div>
</body>
</html>
"""
    
    def _create_report_email_text(self, report: WeeklyReportResult) -> str:
        """리포트 알림 이메일 텍스트 생성"""
        evaluation_text = "긍정적" if report.evaluation == "positive" else "부정적"
        feedback_text = "\n".join([f"- {fb}" for fb in report.feedback[:5]])
        
        return f"""
{report.nickname}님의 주간 감정 분석이 완료되었습니다.

분석 기간: {report.week_start} ~ {report.week_end}
평균 감정 점수: {report.average_score}/10
전반적인 평가: {evaluation_text}

주요 피드백:
{feedback_text}

전체 리포트 보기: {self.api_base_url}/report/{report.user_id}

---
이 이메일은 주간 감정 분석 서비스에서 자동으로 발송되었습니다.
"""
    
    def send_report_notification(
        self,
        recipient_email: str,
        report: WeeklyReportResult,
        max_retries: int = 2
    ) -> bool:
        """
        리포트 완료 알림 이메일을 발송합니다.
        
        Args:
            recipient_email: 수신자 이메일
            report: 주간 리포트 결과
            max_retries: 최대 재시도 횟수
            
        Returns:
            발송 성공 여부
        """
        retry_delays = [1, 2]
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                response = self.client.send_email(
                    Source=self.sender_email,
                    Destination={
                        "ToAddresses": [recipient_email]
                    },
                    Message={
                        "Subject": {
                            "Data": f"📊 {report.nickname}님의 주간 감정 분석이 완료되었습니다",
                            "Charset": "UTF-8"
                        },
                        "Body": {
                            "Text": {
                                "Data": self._create_report_email_text(report),
                                "Charset": "UTF-8"
                            },
                            "Html": {
                                "Data": self._create_report_email_html(report),
                                "Charset": "UTF-8"
                            }
                        }
                    }
                )
                
                logger.info(f"이메일 발송 성공: {recipient_email}, MessageId: {response.get('MessageId')}")
                return True
                
            except Exception as e:
                last_error = e
                logger.warning(f"이메일 발송 실패 (시도 {attempt + 1}/{max_retries + 1}): {e}")
                
                if attempt < max_retries:
                    time.sleep(retry_delays[attempt])
                continue
        
        logger.error(f"이메일 발송 최종 실패: {recipient_email}, 에러: {last_error}")
        return False


@lru_cache()
def get_email_service() -> EmailService:
    """이메일 서비스 싱글톤 인스턴스 반환"""
    return EmailService()
