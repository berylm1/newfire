#!/bin/bash
set -e

echo "🧹 Cleaning up any existing resources..."
kubectl delete kafka data-cluster -n data-infrastructure 2>/dev/null || true
helm uninstall strimzi-kafka-operator -n data-infrastructure 2>/dev/null || true

echo "⏳ Waiting for cleanup (30 seconds)..."
sleep 30

echo ""
echo "📦 Installing Strimzi operator..."
helm install strimzi-kafka-operator strimzi/strimzi-kafka-operator \
  --namespace data-infrastructure \
  --version 0.43.0 \
  --set watchNamespaces={data-infrastructure} \
  --set logLevel=INFO \
  --wait \
  --timeout=5m

echo ""
echo "⏳ Waiting for operator to be fully ready..."
kubectl wait pod \
  -n data-infrastructure \
  -l name=strimzi-cluster-operator \
  --for=condition=Ready \
  --timeout=300s

echo ""
echo "☕ Deploying Kafka cluster..."
kubectl apply -f kafka-stable.yaml

echo ""
echo "📊 Monitoring deployment (this will take 3-5 minutes)..."
echo "Press Ctrl+C to stop watching (deployment will continue in background)"
kubectl get pods -n data-infrastructure -w
