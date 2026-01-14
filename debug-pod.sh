#!/bin/bash
# Pod 디버깅 스크립트

echo "=== Pod 상태 확인 ==="
kubectl get pods -n default -l app=weekly-report

echo ""
echo "=== Pod 상세 정보 ==="
kubectl describe pod -n default -l app=weekly-report

echo ""
echo "=== Pod 로그 ==="
kubectl logs -n default -l app=weekly-report --tail=100

echo ""
echo "=== Pod 이벤트 ==="
kubectl get events -n default --sort-by='.lastTimestamp' | grep weekly-report | tail -20

echo ""
echo "=== Deployment 상태 ==="
kubectl get deployment weekly-report -n default -o yaml | grep -A 10 "status:"

echo ""
echo "=== ReplicaSet 상태 ==="
kubectl get rs -n default -l app=weekly-report
