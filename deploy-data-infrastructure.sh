#!/bin/bash
# deploy-data-infrastructure.sh

set -e

echo "🚀 Deploying Data Infrastructure on Kubernetes"
echo "=============================================="
echo ""

# Install Strimzi Operator
echo "📦 Installing Strimzi Kafka Operator..."
helm install strimzi-kafka-operator strimzi/strimzi-kafka-operator \
  --namespace data-infrastructure \
  --set watchNamespaces={data-infrastructure} \
  --wait

echo "✅ Strimzi operator installed"
echo ""

# Deploy Kafka
echo "☕ Deploying Kafka cluster..."
kubectl apply -f kafka-lightweight.yaml

echo "⏳ Waiting for Kafka to be ready (this takes 3-5 minutes)..."
kubectl wait kafka/data-cluster \
  --for=condition=Ready \
  --timeout=600s \
  -n data-infrastructure

echo "✅ Kafka is ready!"
echo ""

# Deploy Temporal
echo "⏰ Deploying Temporal..."
helm install temporal temporal/temporal \
  --namespace data-infrastructure \
  -f temporal-values.yaml \
  --wait \
  --timeout=10m

echo "✅ Temporal is ready!"
echo ""

# Verification
echo "🎉 Deployment Complete! Verification:"
echo "====================================="
echo ""

echo "Kafka Pods:"
kubectl get pods -n data-infrastructure -l strimzi.io/cluster=data-cluster
echo ""

echo "Temporal Pods:"
kubectl get pods -n data-infrastructure -l app.kubernetes.io/instance=temporal
echo ""

echo "All Pods:"
kubectl get pods -n data-infrastructure
echo ""

echo "Services:"
kubectl get svc -n data-infrastructure
echo ""

echo "Persistent Volumes:"
kubectl get pvc -n data-infrastructure
echo ""

echo "📝 Next Steps:"
echo "  1. Test Kafka: kubectl run kafka-producer -ti --image=quay.io/strimzi/kafka:0.38.0-kafka-3.6.0 --rm=true --restart=Never -n data-infrastructure -- bin/kafka-console-producer.sh --bootstrap-server data-cluster-kafka-bootstrap:9092 --topic test"
echo "  2. Access Temporal Web: kubectl port-forward -n data-infrastructure svc/temporal-web 8080:8080"
echo "  3. View resources: kubectl get all -n data-infrastructure"
