#!/bin/bash

# Exit immediately if any command fails
set -e

# Install K3D
echo "Installing K3D..."
curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash

# Create K3D Cluster without Traefik
echo "Create K3D Cluster..."
k3d cluster create ctf-cluster \
    --agents 3 \
    --k3s-arg "--disable=traefik@server:0" \
    --port 80:80@loadbalancer --port 443:443@loadbalancer

# Run YugabyteDB on same network as K3D cluster
K3D_NETWORK=$(docker network ls | grep k3d-ctf-cluster | awk '{print $2}')
echo "Running YugabyteDB on K3D network..."
docker run -d --name yugabyte --network $K3D_NETWORK -p7000:7000 -p9000:9000 -p15433:15433 -p5433:5433 -p9042:9042 \
    yugabytedb/yugabyte:2.23.1.0-b220 bin/yugabyted start \
    --background=false

# Install Python virtual environment package
echo "Installing virtual environment package..."
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip

# Create and activate a virtual environment
echo "Creating and activating Python virtual environment..."
python3 -m venv ./venv
source ./venv/bin/activate

# Install pip requirements in the virtual environment
echo "Installing Python dependencies..."
pip install --no-cache-dir -r ../database/requirements.txt

# Run database initialization script
echo "Initializing database schema..."
python ../database/create_tables.py
echo "Populating database with fake data..."
python ../database/fake_data.py

# Deactivate virtual environment
deactivate

# Create Kubernetes Namespace
echo "Create Kubernetes Namespace..."
kubectl create namespace project
kubectl config set-context --current --namespace=project

# Install Istio
echo "Install Istio..."
curl -L https://istio.io/downloadIstio | sh -
ISTIO_DIR=$(find $PWD -type d -name "istio-*" -print -quit)
export PATH=$ISTIO_DIR/bin:$PATH
istioctl install --set profile=default -y
kubectl label namespace project istio-injection=enabled

# Deploy Kubernetes manifests
echo "Apply Kubernetes manifests..."
find ./kubernetes -name "*.yaml" -exec kubectl apply -f {} \;

# Build Docker images for each service
echo "Build Docker images for each service..."
docker build -t comp:latest ../../services/competition
docker build -t ctf:latest ../../services/ctf
docker build -t user:latest ../../services/user

# Import Docker images into the K3D cluster
echo "Import Docker images into K3D..."
k3d image import comp:latest -c ctf-cluster
k3d image import ctf:latest -c ctf-cluster
k3d image import user:latest -c ctf-cluster

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
