#!/bin/bash

# FastAPI + Nginx Auto-Deploy Script
# Triggered by GitHub Webhook POST /webhook/github

# Exit immediately if a command exits with a non-zero status
set -e

echo "=================================================="
echo "Deployment started at: $(date)"
echo "Current directory: $(pwd)"
echo "=================================================="

# 1. Update source code from Git
# NOTE: Ensure the deploy key or SSH agent is properly configured on the VM 
# and the git repository is already cloned in this directory.
if [ -d ".git" ]; then
    echo "[Step 1] Pulling latest changes from Git..."
    # Avoid Git "dubious ownership" error in containerized environments
    git config --global --add safe.directory "$(pwd)" || true
    # Reset any local uncommitted changes if desired (caution: comment out if not wanted)
    # git reset --hard HEAD
    git pull origin main
else
    echo "[Step 1 Info] Not a git repository. Skipping git pull."
fi

# 2. Re-deploy the application
# Choose the deployment method that fits your environment:

# --- METHOD A: Docker Compose Deployment (Recommended) ---
if command -v docker &> /dev/null && [ -f "docker-compose.yml" ]; then
    echo "[Step 2] Docker Compose detected. Rebuilding and restarting containers..."
    
    # Try 'docker compose' (v2) and fallback to 'docker-compose' (v1)
    if docker compose version &> /dev/null; then
        echo "Running: docker compose up -d --build"
        docker compose up -d --build
    else
        echo "Running: docker-compose up -d --build"
        docker-compose up -d --build
    fi

# --- METHOD B: Native VM Deployment (Systemd / Pip / Uvicorn) ---
else
    echo "[Step 2] Native deployment or Systemd mode. Restarting services..."
    
    # 1. Activate virtual environment if it exists and install new dependencies
    if [ -d "venv" ]; then
        echo "Activating virtual environment and updating dependencies..."
        source venv/bin/activate
        pip install --no-cache-dir -r requirements.txt
    elif [ -f "requirements.txt" ]; then
        echo "Updating system-wide dependencies..."
        pip install --no-cache-dir -r requirements.txt
    fi
    
    # 2. Restart Systemd service for FastAPI
    # NOTE: Change 'fastapi.service' to match your actual systemd service name.
    # The deploy user must have passwordless sudo permissions for this command.
    SERVICE_NAME="fastapi.service"
    if systemctl is-active --quiet "$SERVICE_NAME" &> /dev/null || systemctl list-unit-files | grep -q "$SERVICE_NAME"; then
        echo "Restarting systemd service: $SERVICE_NAME"
        sudo systemctl restart "$SERVICE_NAME"
        
        # Also restart Nginx if needed
        # sudo systemctl restart nginx
    else
        echo "[Step 2 Warning] Systemd service '$SERVICE_NAME' not found or inactive. Please configure it or run FastAPI manually."
    fi
fi

echo "=================================================="
echo "Deployment successfully completed at: $(date)"
echo "=================================================="
