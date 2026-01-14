# GitHub Secrets 설정 가이드

이 프로젝트는 민감한 정보를 GitHub Secrets로 관리합니다.

## 필수 GitHub Secrets

GitHub 저장소의 Settings > Secrets and variables > Actions에서 다음 secrets를 추가하세요:

### AWS 인증
- `AWS_ACCESS_KEY_ID`: AWS 액세스 키 ID
- `AWS_SECRET_ACCESS_KEY`: AWS 시크릿 액세스 키

### 애플리케이션 설정
- `DB_SECRET_NAME`: AWS Secrets Manager의 DB 비밀번호 시크릿 이름
  - 예: `library-api/db-password`
  
- `BEDROCK_FLOW_ID`: AWS Bedrock Flow ID
  - 예: `BZKT7TJGPT`
  
- `BEDROCK_FLOW_ALIAS_ID`: AWS Bedrock Flow Alias ID
  - 예: `QENFHYZ1KE`
  
- `COGNITO_USER_POOL_ID`: AWS Cognito User Pool ID
  - 예: `us-east-1_xxxxxxxxx`
  
- `COGNITO_CLIENT_ID`: AWS Cognito Client ID
  - 예: `xxxxxxxxxxxxxxxxxxxxxxxxxx`

## 로컬 개발 환경

로컬에서 테스트할 때는 `k8s/secret.yaml`을 생성하세요:

```bash
kubectl create secret generic weekly-report-secrets \
  --from-literal=db-secret-name="library-api/db-password" \
  --from-literal=bedrock-flow-id="YOUR_BEDROCK_FLOW_ID" \
  --from-literal=bedrock-flow-alias-id="YOUR_BEDROCK_FLOW_ALIAS_ID" \
  --from-literal=cognito-user-pool-id="YOUR_COGNITO_USER_POOL_ID" \
  --from-literal=cognito-client-id="YOUR_COGNITO_CLIENT_ID" \
  --namespace=default
```

또는 `k8s/secret.yaml.example`을 복사하여 사용:

```bash
cp k8s/secret.yaml.example k8s/secret.yaml
# 실제 값으로 수정 후
kubectl apply -f k8s/secret.yaml
```

**주의**: `k8s/secret.yaml`은 `.gitignore`에 포함되어 있어 Git에 커밋되지 않습니다.
