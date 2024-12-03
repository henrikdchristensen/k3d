#!/bin/bash

# Exit immediately if any command fails
set -e

# Run Yugabyte
docker run -d --name yugabyte -p5433:5433 \
 yugabytedb/yugabyte:2.23.1.0-b220 bin/yugabyted start \
 --background=false

# Check if K3D is installed
echo "Installing K3D..."
curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash

# Create K3D Cluster with 3 nodes (using Traefik)
echo "Creating K3D cluster with 3 nodes..."
k3d cluster create my-cluster \
    --agents 3 \
    --port "8080:30080@agent:0" \
    --port "8081:30081@agent:1" \
    --port "8082:30082@agent:2"

# Create a namespace for the deployment
kubectl create namespace project
kubectl config set-context --current --namespace=project

# Build Docker images for each service
echo "Building Docker images..."
docker build -t comp:latest ./src/services/competition
docker build -t ctf:latest ./src/services/ctf
docker build -t user:latest ./src/services/user

# Import Docker images into the K3D cluster
echo "Importing Docker images into K3D..."
k3d image import comp:latest -c my-cluster
k3d image import ctf:latest -c my-cluster
k3d image import user:latest -c my-cluster

# Deploy Kubernetes manifests
echo "Applying Kubernetes manifests..."
find ./src/kubernetes-k3d -name "*.yaml" -exec kubectl apply -f {} \;

# Verify the deployment
echo "Verifying deployment..."
kubectl cluster-info
kubectl get pods -A
kubectl get services -A
kubectl get ingress -A
kubectl get svc -A

echo "Deployment completed successfully!"