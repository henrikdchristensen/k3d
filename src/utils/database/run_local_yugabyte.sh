#!/bin/bash

# Variables
CONTAINER_NAME="yugabyte"
IMAGE_NAME="yugabytedb/yugabyte:2.23.1.0-b220"
DATA_DIR="$HOME/yb_data"
PORTS="-p7000:7000 -p9000:9000 -p15433:15433 -p5433:5433 -p9042:9042"

# Stop and remove the existing container if it exists
if [ "$(docker ps -q -f name=$CONTAINER_NAME)" ]; then
  echo "Stopping and removing the existing $CONTAINER_NAME container..."
  docker stop $CONTAINER_NAME
  docker rm $CONTAINER_NAME
fi

# Remove the associated volume (if exists)
echo "Removing unused Docker volumes..."
docker volume prune -f

# Remove the existing data directory if it exists
if [ -d "$DATA_DIR" ]; then
  echo "Removing existing data directory at $DATA_DIR..."
  sudo rm -rf "$DATA_DIR"
fi

# Create a fresh data directory
echo "Creating fresh data directory at $DATA_DIR..."
mkdir -p "$DATA_DIR"

# Ensure the directory is writable by the current user
echo "Setting ownership of $DATA_DIR to the current user..."
sudo chown -R $(whoami):$(whoami) "$DATA_DIR"

# Run the YugabyteDB container
echo "Starting YugabyteDB container..."
docker run -d --name "$CONTAINER_NAME" \
  $PORTS \
  -v "$DATA_DIR:/home/yugabyte/yb_data" \
  "$IMAGE_NAME" bin/yugabyted start \
  --base_dir=/home/yugabyte/yb_data \
  --background=false

# Verify if the container started successfully
if [ "$(docker ps -q -f name=$CONTAINER_NAME)" ]; then
  echo "YugabyteDB container started successfully."
  echo "Access the Admin Console at http://localhost:9000"
else
  echo "Failed to start the YugabyteDB container."
fi
