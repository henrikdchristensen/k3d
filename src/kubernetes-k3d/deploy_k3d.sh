#!/bin/bash

# Exit immediately if any command fails
set -e

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

# Get the K3D Docker network name
K3D_NETWORK=$(docker network ls | grep k3d-my-cluster | awk '{print $2}')

# Run YugabyteDB on the same network
echo "Running YugabyteDB on the K3D network ($K3D_NETWORK)..."
docker run -d --name yugabyte --network $K3D_NETWORK -p5433:5433 \
    yugabytedb/yugabyte:2.23.1.0-b220 bin/yugabyted start \
    --background=false

# Install Python virtual environment package
echo "Installing virtual environment package..."
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip

# Create and activate a virtual environment
echo "Creating and activating Python virtual environment..."
python3 -m venv ./src/database/venv
source ./src/database/venv/bin/activate

# Install pip requirements in the virtual environment
echo "Installing Python dependencies..."
pip install --no-cache-dir -r ./src/database/requirements.txt

echo "Waiting for 10 seconds to allow database to start..."
sleep 10
echo "Done waiting!"

# Run database initialization script
echo "Initializing database schema..."
python ./src/database/create_tables.py

# Deactivate virtual environment
deactivate

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

echo "Waiting for 10 seconds to allow services to start..."
sleep 10
echo "Done waiting!"

# Verify the deployment
echo "Verifying deployment..."
kubectl get pods -A
kubectl get services -A
kubectl get ingress -A
kubectl get svc -A

echo "Deployment completed successfully!"
