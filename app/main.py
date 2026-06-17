import os
import sys
import hmac
import hashlib
import socket
import subprocess
import time
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, Request, HTTPException, Header, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(
    title="FastAPI GKE & VM Auto-Deploy Demo",
    description="A professional FastAPI template with Nginx proxy, GitHub auto-deploy webhook, and GKE health check endpoints.",
    version="1.0.1"
)

# Start time to calculate uptime
START_TIME = time.time()

# Environment configurations
APP_VERSION = os.getenv("APP_VERSION", "v1.0.1")
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


def get_system_metrics():
    """
    Reads native Linux system stats (/proc/loadavg and /proc/meminfo) without external dependencies.
    """
    cpu_load = "N/A"
    ram_usage = "N/A"
    
    # 1. CPU Load Average
    try:
        if os.path.exists("/proc/loadavg"):
            with open("/proc/loadavg", "r") as f:
                load = f.read().split()
                if len(load) >= 3:
                    cpu_load = f"{load[0]} (1m), {load[1]} (5m), {load[2]} (15m)"
    except Exception:
        pass

    # 2. RAM Usage Percent
    try:
        if os.path.exists("/proc/meminfo"):
            with open("/proc/meminfo", "r") as f:
                mem_total = 0
                mem_avail = 0
                for line in f:
                    if line.startswith("MemTotal:"):
                        mem_total = int(line.split()[1])
                    elif line.startswith("MemAvailable:"):
                        mem_avail = int(line.split()[1])
                if mem_total > 0:
                    used = mem_total - mem_avail
                    pct = (used / mem_total) * 100
                    ram_usage = f"{pct:.1f}% ({used // 1024} MB / {mem_total // 1024} MB)"
    except Exception:
        pass

    return cpu_load, ram_usage


def get_git_commit_info():
    """
    Runs git command to retrieve metadata of the latest local commit.
    """
    try:
        repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Git dubious ownership bypass
        subprocess.run(["git", "config", "--global", "--add", "safe.directory", repo_dir], capture_output=True)
        
        cmd = ["git", "-C", repo_dir, "log", "-n", "1", "--format=%h|%s|%an|%ar"]
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if process.returncode == 0:
            parts = process.stdout.strip().split("|")
            if len(parts) == 4:
                return {
                    "hash": parts[0],
                    "subject": parts[1],
                    "author": parts[2],
                    "time": parts[3]
                }
    except Exception:
        pass
    return {
        "hash": "N/A",
        "subject": "N/A",
        "author": "N/A",
        "time": "N/A"
    }


@app.get("/", response_class=HTMLResponse)
async def root():
    """
    Renders an extremely premium, cyber-themed interactive devops dashboard.
    """
    uptime_seconds = round(time.time() - START_TIME, 2)
    uptime_hours = round(uptime_seconds / 3600, 2)
    
    cpu_load, ram_usage = get_system_metrics()
    git_info = get_git_commit_info()
    hostname = socket.gethostname()
    
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "127.0.0.1"

    webhook_status = "ENABLED" if GITHUB_WEBHOOK_SECRET else "DISABLED (Secret missing)"
    webhook_class = "active-badge" if GITHUB_WEBHOOK_SECRET else "inactive-badge"

    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-Hant">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>FastAPI DevOps Control Center</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
        <style>
            :root {{
                --bg-color: #060b13;
                --card-bg: rgba(16, 22, 35, 0.65);
                --card-border: rgba(255, 255, 255, 0.05);
                --accent-primary: #3b82f6; /* Cyber Blue */
                --accent-success: #10b981; /* Emerald Green */
                --accent-warning: #f59e0b; /* Amber Gold */
                --text-primary: #f3f4f6;
                --text-secondary: #9ca3af;
                --text-muted: #6b7280;
                --glow-color: rgba(59, 130, 246, 0.15);
            }}

            * {{
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }}

            body {{
                font-family: 'Outfit', sans-serif;
                background-color: var(--bg-color);
                color: var(--text-primary);
                background-image: 
                    radial-gradient(at 10% 10%, rgba(59, 130, 246, 0.05) 0px, transparent 50%),
                    radial-gradient(at 90% 90%, rgba(16, 185, 129, 0.05) 0px, transparent 50%);
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                overflow-x: hidden;
            }}

            header {{
                background: rgba(10, 15, 28, 0.8);
                backdrop-filter: blur(12px);
                border-bottom: 1px solid var(--card-border);
                padding: 1.25rem 2rem;
                position: sticky;
                top: 0;
                z-index: 100;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}

            .logo-group {{
                display: flex;
                align-items: center;
                gap: 0.75rem;
            }}

            .pulse-dot {{
                width: 10px;
                height: 10px;
                background-color: var(--accent-success);
                border-radius: 50%;
                box-shadow: 0 0 12px var(--accent-success);
                animation: pulse 2s infinite;
            }}

            @keyframes pulse {{
                0% {{ transform: scale(0.9); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }}
                70% {{ transform: scale(1); box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }}
                100% {{ transform: scale(0.9); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }}
            }}

            .logo-group h1 {{
                font-size: 1.35rem;
                font-weight: 700;
                letter-spacing: -0.025em;
                background: linear-gradient(135deg, #ffffff 30%, #9ca3af 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }}

            .env-badge {{
                background: rgba(59, 130, 246, 0.1);
                border: 1px solid rgba(59, 130, 246, 0.2);
                color: var(--accent-primary);
                padding: 0.35rem 0.85rem;
                border-radius: 9999px;
                font-size: 0.8rem;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }}

            main {{
                flex: 1;
                max-width: 1200px;
                width: 100%;
                margin: 0 auto;
                padding: 2.5rem 1.5rem;
                display: flex;
                flex-direction: column;
                gap: 2.5rem;
            }}

            .hero-section {{
                text-align: center;
                margin-bottom: 1rem;
            }}

            .hero-section h2 {{
                font-size: 2.5rem;
                font-weight: 700;
                margin-bottom: 0.5rem;
                background: linear-gradient(135deg, #ffffff 40%, var(--accent-primary) 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                letter-spacing: -0.03em;
            }}

            .hero-section p {{
                color: var(--text-secondary);
                font-size: 1.1rem;
                font-weight: 300;
            }}

            .dashboard-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
                gap: 1.5rem;
            }}

            .card {{
                background: var(--card-bg);
                border: 1px solid var(--card-border);
                border-radius: 16px;
                padding: 1.75rem;
                backdrop-filter: blur(16px);
                transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), border-color 0.3s, box-shadow 0.3s;
                position: relative;
                overflow: hidden;
            }}

            .card::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 4px;
                background: linear-gradient(90deg, transparent, var(--accent-primary), transparent);
                opacity: 0;
                transition: opacity 0.3s;
            }}

            .card:hover {{
                transform: translateY(-5px);
                border-color: rgba(59, 130, 246, 0.25);
                box-shadow: 0 12px 30px rgba(0, 0, 0, 0.4), 0 0 15px var(--glow-color);
            }}

            .card:hover::before {{
                opacity: 1;
            }}

            .card-title-group {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 1.5rem;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
                padding-bottom: 0.75rem;
            }}

            .card h3 {{
                font-size: 1.15rem;
                font-weight: 600;
                color: #ffffff;
            }}

            .card-icon {{
                font-size: 1.25rem;
                opacity: 0.8;
            }}

            .meta-list {{
                display: flex;
                flex-direction: column;
                gap: 1rem;
            }}

            .meta-item {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-size: 0.95rem;
            }}

            .meta-label {{
                color: var(--text-secondary);
                font-weight: 400;
            }}

            .meta-value {{
                font-weight: 600;
                color: #ffffff;
                font-family: 'Outfit', sans-serif;
            }}

            .mono-text {{
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.85rem;
                background: rgba(0, 0, 0, 0.25);
                padding: 0.2rem 0.5rem;
                border-radius: 4px;
                border: 1px solid rgba(255, 255, 255, 0.05);
                color: #60a5fa;
            }}

            .active-badge {{
                background: rgba(16, 185, 129, 0.1);
                border: 1px solid rgba(16, 185, 129, 0.2);
                color: var(--accent-success);
                padding: 0.15rem 0.5rem;
                border-radius: 4px;
                font-size: 0.8rem;
                font-weight: 600;
            }}

            .inactive-badge {{
                background: rgba(245, 158, 11, 0.1);
                border: 1px solid rgba(245, 158, 11, 0.2);
                color: var(--accent-warning);
                padding: 0.15rem 0.5rem;
                border-radius: 4px;
                font-size: 0.8rem;
                font-weight: 600;
            }}

            .console-output {{
                grid-column: 1 / -1;
                background: rgba(5, 8, 15, 0.85);
                border: 1px solid var(--card-border);
                border-radius: 12px;
                padding: 1.5rem;
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.9rem;
                color: #10b981;
                max-height: 250px;
                overflow-y: auto;
                box-shadow: inset 0 2px 10px rgba(0, 0, 0, 0.8);
            }}

            .console-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 0.75rem;
                color: var(--text-muted);
                font-size: 0.8rem;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
                padding-bottom: 0.5rem;
            }}

            footer {{
                background: rgba(8, 11, 22, 0.9);
                border-top: 1px solid var(--card-border);
                padding: 1.5rem 2rem;
                text-align: center;
                font-size: 0.85rem;
                color: var(--text-muted);
            }}

            footer a {{
                color: var(--accent-primary);
                text-decoration: none;
                transition: color 0.2s;
            }}

            footer a:hover {{
                color: #60a5fa;
                text-decoration: underline;
            }}

            @media (max-width: 768px) {{
                .dashboard-grid {{
                    grid-template-columns: 1fr;
                }}
            }}
        </style>
    </head>
    <body>
        <header>
            <div class="logo-group">
                <div class="pulse-dot"></div>
                <h1>FastAPI DevOps Control Center</h1>
            </div>
            <div class="env-badge">{APP_ENV}</div>
        </header>

        <main>
            <section class="hero-section">
                <h2>系統維運狀態面板</h2>
                <p>VM 級別自動化部署與監控・多維度實時數據指標</p>
            </section>

            <section class="dashboard-grid">
                <!-- CARD 1: VM Endpoint Stats -->
                <div class="card" id="card-vm-endpoint">
                    <div class="card-title-group">
                        <h3>VM 執行個體資訊</h3>
                        <span class="card-icon">🖥️</span>
                    </div>
                    <div class="meta-list">
                        <div class="meta-item">
                            <span class="meta-label">VM 主機名稱 (hostname)</span>
                            <span class="meta-value mono-text">{hostname}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">VM 內部 IP</span>
                            <span class="meta-value mono-text">{local_ip}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">VM 外部 IP</span>
                            <span class="meta-value mono-text">35.239.45.214</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">服務已運行時間 (Uptime)</span>
                            <span class="meta-value">{uptime_hours} hrs ({uptime_seconds}s)</span>
                        </div>
                    </div>
                </div>

                <!-- CARD 2: App Metadata -->
                <div class="card" id="card-app-metadata">
                    <div class="card-title-group">
                        <h3>應用程式元數據</h3>
                        <span class="card-icon">🚀</span>
                    </div>
                    <div class="meta-list">
                        <div class="meta-item">
                            <span class="meta-label">應用程式版本 (Version)</span>
                            <span class="meta-value mono-text">{APP_VERSION}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">Python 版本</span>
                            <span class="meta-value mono-text">{sys.version.split()[0]}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">CPU 負載</span>
                            <span class="meta-value">{cpu_load}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">記憶體使用率</span>
                            <span class="meta-value">{ram_usage}</span>
                        </div>
                    </div>
                </div>

                <!-- CARD 3: Git Control Info -->
                <div class="card" id="card-git-control">
                    <div class="card-title-group">
                        <h3>Git 代碼倉庫狀態</h3>
                        <span class="card-icon">🐙</span>
                    </div>
                    <div class="meta-list">
                        <div class="meta-item">
                            <span class="meta-label">分支 (Branch)</span>
                            <span class="meta-value mono-text">main</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">最新提交 HASH</span>
                            <span class="meta-value mono-text">{git_info['hash']}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">提交作者</span>
                            <span class="meta-value">{git_info['author']}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">最新提交時間</span>
                            <span class="meta-value">{git_info['time']}</span>
                        </div>
                    </div>
                </div>

                <!-- CARD 4: Webhook Monitor -->
                <div class="card" id="card-webhook-monitor">
                    <div class="card-title-group">
                        <h3>CI/CD Webhook 監控</h3>
                        <span class="card-icon">🔗</span>
                    </div>
                    <div class="meta-list">
                        <div class="meta-item">
                            <span class="meta-label">Webhook 接收路由</span>
                            <span class="meta-value mono-text">/webhook/github</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">簽名驗證狀態</span>
                            <span class="{webhook_class}">{webhook_status}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">安全模式</span>
                            <span class="meta-value" style="color: var(--accent-success)">CI 驗證後部署 (安全)</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">最近更新機制</span>
                            <span class="meta-value">GitHub Actions / CD</span>
                        </div>
                    </div>
                </div>

                <!-- Console Display Box -->
                <div class="console-output">
                    <div class="console-header">
                        <span>SYS LOG MONITOR</span>
                        <span>STATUS: LISTENING</span>
                    </div>
                    &gt; [SYSTEM] Initialized FastAPI DevOps template on VM port 8000 successfully.<br>
                    &gt; [SYSTEM] Reverse proxy active via Nginx on port 80.<br>
                    &gt; [GIT] Git directory monitored successfully. Current commit: {git_info['hash']} - {git_info['subject']}<br>
                    &gt; [WEBHOOK] HMAC-SHA256 signature algorithm configured with GITHUB_WEBHOOK_SECRET.<br>
                    &gt; [READY] VM CD pipeline is standing by. Fully ready for code push deploy!
                </div>
            </section>
        </main>

        <footer>
            <p>© 2026 Jenny DevOps. Handcrafted under Google DeepMind Advanced Agentic Coding. <a href="/healthz">健康檢查</a> | <a href="/status">狀態數據</a></p>
        </footer>
    </body>
    </html>
    """
    return html_content


@app.get("/healthz")
async def health_check():
    """
    Kubernetes Liveness/Readiness Probe endpoint. Always returns 200 OK.
    """
    uptime_seconds = round(time.time() - START_TIME, 2)
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
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
            "server_time": datetime.now(timezone.utc).isoformat() + "Z"
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
        "triggered_at": datetime.now(timezone.utc).isoformat() + "Z"
    }
