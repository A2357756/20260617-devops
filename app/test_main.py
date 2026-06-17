import hmac
import hashlib
import json
from fastapi.testclient import TestClient
from app.main import app, GITHUB_WEBHOOK_SECRET

client = TestClient(app)

def test_read_root():
    """
    Test that the root endpoint returns a beautiful HTML dashboard.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "FastAPI DevOps Control Center" in response.text
    assert "35.239.45.214" in response.text

def test_healthz():
    """
    Test the health check endpoint.
    """
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "uptime_seconds" in data

def test_status():
    """
    Test the status endpoint.
    """
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert "app_info" in data
    assert "system_info" in data
    assert data["app_info"]["environment"] == "production"

def test_webhook_no_signature():
    """
    Test webhook endpoint without signature.
    If GITHUB_WEBHOOK_SECRET is set, it should return 401.
    If not set, it should allow the request.
    """
    response = client.post("/webhook/github", json={"test": "data"})
    if GITHUB_WEBHOOK_SECRET:
        assert response.status_code == 401
    else:
        assert response.status_code == 200

def test_webhook_invalid_signature():
    """
    Test webhook endpoint with invalid signature.
    If GITHUB_WEBHOOK_SECRET is set, it should return 403.
    """
    if GITHUB_WEBHOOK_SECRET:
        response = client.post(
            "/webhook/github",
            json={"test": "data"},
            headers={"X-Hub-Signature-256": "sha256=invalid"}
        )
        assert response.status_code == 403

def test_webhook_valid_signature_ping():
    """
    Test webhook endpoint with valid signature for ping event.
    """
    secret = GITHUB_WEBHOOK_SECRET or "testsecret"
    # Temporarily override GITHUB_WEBHOOK_SECRET for reliable test execution
    import app.main
    original_secret = app.main.GITHUB_WEBHOOK_SECRET
    app.main.GITHUB_WEBHOOK_SECRET = secret

    payload = {"test": "data"}
    payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    signature = "sha256=" + hmac.new(
        key=secret.encode("utf-8"),
        msg=payload_bytes,
        digestmod=hashlib.sha256
    ).hexdigest()

    response = client.post(
        "/webhook/github",
        content=payload_bytes,
        headers={
            "X-Hub-Signature-256": signature,
            "X-GitHub-Event": "ping",
            "Content-Type": "application/json"
        }
    )
    assert response.status_code == 200
    assert response.json()["message"] == "GitHub connection successful (ping event received)"

    # Restore original secret
    app.main.GITHUB_WEBHOOK_SECRET = original_secret
