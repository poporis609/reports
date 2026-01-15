"""
S3 서비스 - 리포트 파일 저장 및 조회
"""
import boto3
import logging
from datetime import datetime
from typing import Optional
from functools import lru_cache

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class S3ServiceError(Exception):
    """S3 서비스 에러"""
    pass


class S3Service:
    """AWS S3를 사용한 리포트 파일 관리 서비스"""
    
    BUCKET_NAME = "knowledge-base-test-6577574"
    
    def __init__(self):
        self.settings = get_settings()
        self.client = boto3.client(
            "s3",
            region_name=self.settings.AWS_REGION
        )
    
    def _generate_s3_key(self, user_id: str, created_at: datetime) -> str:
        """
        S3 키를 생성합니다.
        형식: {cognito_sub}/{년도}/{월}/report_{작성일}.txt
        """
        year = created_at.strftime("%Y")
        month = created_at.strftime("%m")
        date_str = created_at.strftime("%Y-%m-%d")
        
        return f"{user_id}/{year}/{month}/report_{date_str}.txt"
    
    def _format_report_content(self, report_data: dict) -> str:
        """
        리포트 데이터를 텍스트 형식으로 변환합니다.
        """
        lines = [
            "=" * 50,
            f"주간 감정 분석 리포트",
            "=" * 50,
            "",
            f"작성자: {report_data.get('nickname', '')}",
            f"분석 기간: {report_data.get('week_start', '')} ~ {report_data.get('week_end', '')}",
            f"생성일: {report_data.get('created_at', '')}",
            "",
            "-" * 50,
            "📊 요약",
            "-" * 50,
            f"평균 점수: {report_data.get('average_score', 0)}/10",
            f"평가: {'긍정적' if report_data.get('evaluation') == 'positive' else '부정적'}",
            "",
            "-" * 50,
            "📅 일별 분석",
            "-" * 50,
        ]
        
        for daily in report_data.get('daily_analysis', []):
            lines.append(f"\n[{daily.get('date', '')}]")
            lines.append(f"  점수: {daily.get('score', 0)}/10")
            lines.append(f"  감정: {daily.get('sentiment', '')}")
            lines.append(f"  내용: {daily.get('diary_content', '')}")
            if daily.get('key_themes'):
                lines.append(f"  테마: {', '.join(daily.get('key_themes', []))}")
        
        lines.extend([
            "",
            "-" * 50,
            "🔍 패턴 분석",
            "-" * 50,
        ])
        
        for pattern in report_data.get('patterns', []):
            correlation = "긍정적" if pattern.get('correlation') == 'positive' else "부정적"
            lines.append(f"  • {pattern.get('value', '')} ({pattern.get('type', '')})")
            lines.append(f"    - 상관관계: {correlation}")
            lines.append(f"    - 빈도: {pattern.get('frequency', 0)}회")
            lines.append(f"    - 평균 점수: {pattern.get('average_score', 0)}")
        
        lines.extend([
            "",
            "-" * 50,
            "💡 피드백",
            "-" * 50,
        ])
        
        for feedback in report_data.get('feedback', []):
            lines.append(f"  • {feedback}")
        
        lines.extend([
            "",
            "=" * 50,
        ])
        
        return "\n".join(lines)
    
    def upload_report(
        self,
        user_id: str,
        report_data: dict,
        created_at: datetime
    ) -> str:
        """
        리포트를 S3에 업로드합니다.
        
        Args:
            user_id: 사용자 ID (Cognito sub)
            report_data: 리포트 데이터
            created_at: 생성 시간
            
        Returns:
            S3 키
        """
        try:
            s3_key = self._generate_s3_key(user_id, created_at)
            content = self._format_report_content(report_data)
            
            self.client.put_object(
                Bucket=self.BUCKET_NAME,
                Key=s3_key,
                Body=content.encode('utf-8'),
                ContentType='text/plain; charset=utf-8'
            )
            
            logger.info(f"리포트 업로드 완료: s3://{self.BUCKET_NAME}/{s3_key}")
            return s3_key
            
        except Exception as e:
            logger.error(f"S3 업로드 실패: {e}")
            raise S3ServiceError(f"리포트 파일 저장 실패: {e}")
    
    def get_report(self, s3_key: str) -> str:
        """
        S3에서 리포트를 조회합니다.
        
        Args:
            s3_key: S3 키
            
        Returns:
            리포트 내용
        """
        try:
            response = self.client.get_object(
                Bucket=self.BUCKET_NAME,
                Key=s3_key
            )
            content = response['Body'].read().decode('utf-8')
            return content
            
        except self.client.exceptions.NoSuchKey:
            raise S3ServiceError(f"리포트 파일을 찾을 수 없습니다: {s3_key}")
        except Exception as e:
            logger.error(f"S3 조회 실패: {e}")
            raise S3ServiceError(f"리포트 파일 조회 실패: {e}")
    
    def delete_report(self, s3_key: str) -> bool:
        """
        S3에서 리포트를 삭제합니다.
        
        Args:
            s3_key: S3 키
            
        Returns:
            삭제 성공 여부
        """
        try:
            self.client.delete_object(
                Bucket=self.BUCKET_NAME,
                Key=s3_key
            )
            logger.info(f"리포트 삭제 완료: s3://{self.BUCKET_NAME}/{s3_key}")
            return True
            
        except Exception as e:
            logger.error(f"S3 삭제 실패: {e}")
            return False
    
    def generate_presigned_url(self, s3_key: str, expiration: int = 3600) -> str:
        """
        S3 객체에 대한 presigned URL을 생성합니다.
        
        Args:
            s3_key: S3 키
            expiration: URL 만료 시간 (초, 기본 1시간)
            
        Returns:
            Presigned URL
        """
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.BUCKET_NAME,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )
            return url
            
        except Exception as e:
            logger.error(f"Presigned URL 생성 실패: {e}")
            raise S3ServiceError(f"다운로드 URL 생성 실패: {e}")


@lru_cache()
def get_s3_service() -> S3Service:
    """S3 서비스 싱글톤 인스턴스 반환"""
    return S3Service()
