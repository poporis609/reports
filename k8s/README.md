# Kubernetes 배포 가이드

## 보안 설정

### 1. Secret 생성

실제 배포 전에 `secret.yaml.example`을 복사하여 `secret.yaml`을 생성하고 실제 값을 입력하세요:

```bash
cp k8s/secret.yaml.example k8s/secret.yaml
```

`secret.yaml` 파일을 편집하여 다음 값들을 실제 값으로 변경:
- `YOUR_BEDROCK_FLOW_ID`
- `YOUR_BEDROCK_FLOW_ALIAS_ID`
- `YOUR_COGNITO_USER_POOL_ID`
- `YOUR_COGNITO_CLIENT_ID`

### 2. Secret 적용

```bash
kubectl apply -f k8s/secret.yaml
```

### 3. ConfigMap 적용

```bash
kubectl apply -f k8s/configmap.yaml
```

### 4. 배포

```bash
kubectl apply -f k8s/serviceaccount.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
```

## 주의사항

- `secret.yaml` 파일은 절대 Git에 커밋하지 마세요
- `.gitignore`에 이미 추가되어 있습니다
- 프로덕션 환경에서는 AWS Secrets Manager나 External Secrets Operator 사용을 권장합니다
