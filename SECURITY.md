# 보안 정책

## 민감 정보 관리

### 환경 변수
- 모든 민감한 정보는 환경 변수로 관리
- `.env` 파일은 Git에 커밋하지 않음
- `.env.example`에 필요한 변수 목록만 제공

### Kubernetes Secrets
- 민감한 설정은 Kubernetes Secret으로 관리
- `k8s/secret.yaml`은 Git에 커밋하지 않음
- `k8s/secret.yaml.example`만 템플릿으로 제공

### AWS Secrets Manager
- 데이터베이스 비밀번호는 AWS Secrets Manager에서 관리
- IAM 역할 기반 접근 제어 사용

## IAM 정책

### 최소 권한 원칙
- 각 서비스는 필요한 최소한의 권한만 부여
- 리소스 ARN을 명시적으로 지정
- 와일드카드(`*`) 사용 최소화

### 정책 파일
- `infra/lambda-policy.json`: Lambda 함수 실행 역할
- `infra/secrets-policy.json`: Secrets Manager 접근 정책
- `infra/weekly-report-policy.json`: EKS Pod 실행 역할

## CORS 설정

### 허용된 Origin
- 프로덕션: `https://aws11.shop`, `https://api.aws11.shop`
- 개발 환경에서만 localhost 허용

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
