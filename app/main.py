import os
import sys
import hmac
import hashlib
import socket
import subprocess
import time
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, Request, HTTPException, Header, BackgroundTasks
from fastapi.responses import JSONResponse

app = FastAPI(
    title="FastAPI GKE & VM Auto-Deploy Demo",
    description="A professional FastAPI template with Nginx proxy, GitHub auto-deploy webhook, and GKE health check endpoints.",
    version="1.0.0"
)

# Start time to calculate uptime
START_TIME = time.time()

# Environment configurations
APP_VERSION = os.getenv("APP_VERSION", "v1.0.0")
APP_ENV = os.getenv("APP_ENV", "production")
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")


def run_deploy_script():
    """
    Executes the deployment script in the background.
    """
    script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "deploy.sh")
    if not os.path.exists(script_path):
        print(f"[Webhook Error] Deployment script not found at: {script_path}")
        return

    print(f"[Webhook] Executing deploy script: {script_path}")
    try:
        # Run deploy script and log output
        process = subprocess.Popen(
            ["bash", script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        print(f"[Webhook Success] exit code: {process.returncode}")
        if stdout:
            print(f"[Webhook stdout]\n{stdout}")
        if stderr:
            print(f"[Webhook stderr]\n{stderr}")
    except Exception as e:
        print(f"[Webhook Exception] Failed to run deploy script: {e}")


def verify_signature(payload: bytes, signature: str) -> bool:
    """
    Verifies the HMAC SHA-256 signature from GitHub Webhook payload.
    """
    if not GITHUB_WEBHOOK_SECRET:
        # If no secret is configured, deny hook validation for safety
        print("[Webhook Warning] GITHUB_WEBHOOK_SECRET environment variable is not set. Verification denied.")
        return False

    if not signature.startswith("sha256="):
        return False

    received_sha = signature.replace("sha256=", "")
    expected_sha = hmac.new(
        key=GITHUB_WEBHOOK_SECRET.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_sha, received_sha)


@app.get("/")
async def root():
    """
    Landing page offering details about available endpoints.
    """
    return {
        "message": "Welcome to the FastAPI + Nginx Demo App!",
        "version": APP_VERSION,
        "environment": APP_ENV,
        "endpoints": {
            "root": "/",
            "health_check": "/healthz",
            "status": "/status",
            "github_webhook": "/webhook/github"
        }
    }


@app.get("/healthz")
async def health_check():
    """
    Kubernetes Liveness/Readiness Probe endpoint. Always returns 200 OK.
    """
    uptime_seconds = round(time.time() - START_TIME, 2)
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "uptime_seconds": uptime_seconds
    }


@app.get("/status")
async def get_status():
    """
    Status endpoint displaying system state & metadata.
    Perfect for showing load balancer rotation in GKE (hostnames will vary).
    """
    hostname = socket.gethostname()
    try:
        # Retrieve primary local IP address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "127.0.0.1"

    return {
        "app_info": {
            "version": APP_VERSION,
            "environment": APP_ENV,
            "python_version": sys.version.split()[0]
        },
        "system_info": {
            "hostname": hostname,
            "local_ip": local_ip,
            "server_time": datetime.utcnow().isoformat() + "Z"
        },
        "kubernetes_demo_note": "Scale your deployment in GKE to multiple replicas, then refresh this page. You will see the hostname/ip change as the K8s Service load balances your requests!"
    }


@app.post("/webhook/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: Optional[str] = Header(None)
):
    """
    GitHub Webhook receiver. 
    Verifies payload signature and triggers background deployment script (deploy.sh).
    """
    # 1. Get raw request body
    payload_body = await request.body()

    # 2. Check if GitHub secret is configured and verify signature
    if GITHUB_WEBHOOK_SECRET:
        if not x_hub_signature_256:
            raise HTTPException(status_code=401, detail="X-Hub-Signature-256 header is missing")
        
        if not verify_signature(payload_body, x_hub_signature_256):
            raise HTTPException(status_code=403, detail="Invalid signature verification")
    else:
        # If secret is empty, log a security warning but allow request for testing
        print("[Webhook Warning] Running WITHOUT webhook signature verification! Please set GITHUB_WEBHOOK_SECRET in production.")

    # 3. Handle GitHub Ping event or Push event
    github_event = request.headers.get("X-GitHub-Event", "push")
    if github_event == "ping":
        return {"status": "success", "message": "GitHub connection successful (ping event received)"}

    # 4. Add the deployment task to background execution to prevent webhook timeouts
    background_tasks.add_task(run_deploy_script)

    return {
        "status": "success",
        "message": "Webhook received successfully. Deployment triggered in the background.",
        "triggered_at": datetime.utcnow().isoformat() + "Z"
    }
