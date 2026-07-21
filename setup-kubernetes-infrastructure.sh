#!/bin/bash
# setup-kubernetes-infrastructure.sh

echo "🎯 Setting up Kubernetes infrastructure..."

# Wait for cluster to be ready
echo "⏳ Waiting for cluster to be ready..."
kubectl wait --for=condition=Ready nodes --all --timeout=300s

# Enable essential addons
echo "🔌 Enabling Minikube addons..."
minikube addons enable storage-provisioner
minikube addons enable default-storageclass
minikube addons enable metrics-server

# Create namespace
echo "📂 Creating namespace..."
kubectl create namespace data-infrastructure

# Create storage class
echo "💾 Creating storage class..."
cat <<EOF | kubectl apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: k8s.io/minikube-hostpath
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
allowVolumeExpansion: true
EOF

# Add Helm repositories
echo "📚 Adding Helm repositories..."
helm repo add strimzi https://strimzi.io/charts/
helm repo add temporal https://temporalio.github.io/helm-charts
helm repo update

# Verify setup
echo ""
echo "✅ Setup complete! Verification:"
echo "================================"
echo ""
kubectl get nodes
echo ""
kubectl get namespaces | grep data-infrastructure
echo ""
kubectl get storageclass
echo ""
helm repo list
echo ""
echo "🎉 Ready to deploy Kafka and Temporal!"
