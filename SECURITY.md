# 보안 정책

## 보안 아키텍처

### AWS Secrets Manager 사용 (권장)
모든 민감한 정보는 **AWS Secrets Manager**에 저장하고, **IRSA (IAM Roles for Service Accounts)**를 통해 접근합니다.

#### 장점:
- ✅ GitHub에 민감 정보 저장 불필요
- ✅ AWS IAM 기반 접근 제어
- ✅ 자동 로테이션 지원
- ✅ 감사 로그 (CloudTrail)
- ✅ 암호화 저장 (KMS)

### Secrets Manager 설정

#### 1. 애플리케이션 설정 Secret 생성

```bash
# infra/setup-secrets-manager.sh 스크립트 실행
chmod +x infra/setup-secrets-manager.sh
./infra/setup-secrets-manager.sh
```

또는 AWS CLI로 직접 생성:

```bash
aws secretsmanager create-secret \
    --name weekly-report/app-config \
    --description "Weekly Report Service Configuration" \
    --secret-string '{
        "BEDROCK_FLOW_ID": "YOUR_ACTUAL_FLOW_ID",
        "BEDROCK_FLOW_ALIAS_ID": "YOUR_ACTUAL_ALIAS_ID",
        "COGNITO_USER_POOL_ID": "YOUR_ACTUAL_POOL_ID",
        "COGNITO_CLIENT_ID": "YOUR_ACTUAL_CLIENT_ID"
    }' \
    --region us-east-1
```

#### 2. IAM 정책 적용

EKS ServiceAccount에 `infra/weekly-report-policy.json` 정책을 연결하여 Secrets Manager 접근 권한 부여

#### 3. 애플리케이션 자동 로드

애플리케이션이 시작될 때 자동으로 Secrets Manager에서 설정을 가져옵니다:
- `app/config/settings.py`: 설정 관리
- `app/config/secrets.py`: Secrets Manager 클라이언트

### 환경 변수

#### ConfigMap (민감하지 않은 정보)
- DB 호스트, 포트, 데이터베이스명, 사용자명
- AWS 리전
- SES 발신자 이메일
- API Base URL

#### Secrets Manager (민감한 정보)
- DB 비밀번호
- Bedrock Flow ID/Alias
- Cognito Pool ID/Client ID

## IAM 정책

### 최소 권한 원칙
- 각 서비스는 필요한 최소한의 권한만 부여
- 리소스 ARN을 명시적으로 지정
- 와일드카드(`*`) 사용 최소화

### 정책 파일
- `infra/lambda-policy.json`: Lambda 함수 실행 역할
- `infra/secrets-policy.json`: Secrets Manager 접근 정책
- `infra/weekly-report-policy.json`: EKS Pod 실행 역할 (IRSA)

## CORS 설정

### 허용된 Origin
- 프로덕션: `https://aws11.shop`, `https://api.aws11.shop`
- 개발 환경에서만 localhost 허용 (`DEBUG=true`일 때)

## 보안 취약점 보고

보안 취약점을 발견하신 경우:
1. 공개 이슈로 등록하지 마세요
2. 담당자에게 직접 연락
3. 상세한 재현 방법 제공

## 정기 보안 점검

- [ ] 의존성 취약점 스캔 (월 1회)
- [ ] IAM 정책 검토 (분기 1회)
- [ ] 접근 로그 분석 (주 1회)
- [ ] Secret 로테이션 (분기 1회)
- [ ] Secrets Manager 감사 로그 확인 (월 1회)
