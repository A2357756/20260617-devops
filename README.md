# FastAPI + Nginx + GitHub Webhook & GKE Demo Project

這個專案是一個完整的、生產就緒（Production-Ready）的 Python FastAPI 網頁伺服器範本。它整合了 **Nginx 反向代理**、**GitHub Webhook 自動部署** 與 **K8s/GKE 容器化展示路由**。

---

## 📂 專案目錄結構

```text
/home/jenny/0617devops/
├── app/
│   ├── __init__.py
│   └── main.py             # FastAPI 核心程式（包含 Webhook、Health、Status 路由）
├── nginx/
│   └── nginx.conf          # Nginx 反向代理設定檔
├── Dockerfile              # FastAPI 專用 Dockerfile (非 Root 安全設定)
├── docker-compose.yml      # 一鍵啟動 Web & Nginx 的 Docker Compose 檔
├── deploy.sh               # GitHub Webhook 觸發的 VM 自動部署腳本
├── requirements.txt        # Python 依賴套件
└── README.md               # 本說明文件
```

---

## 🚀 快速啟動專案 (Docker Compose)

在已安裝 Docker 與 Docker Compose 的 VM 或本機環境中，只需一行指令即可一鍵啟動 FastAPI + Nginx：

```bash
docker compose up -d --build
```

*   **FastAPI 服務** 將運行在內部 `8000` 端口。
*   **Nginx 服務** 監聽外部 `80` 端口，並自動將流量轉發至 FastAPI。
*   請在瀏覽器或以 `curl` 存取：`http://<您的IP>/`

---

## 🛠 需求 1：主要 API 路由說明

| 路由路徑 | HTTP 方法 | 功能描述 | 用途 |
| :--- | :--- | :--- | :--- |
| `/` | `GET` | 歡迎頁面與 API 清單 | 檢查連線是否正常 |
| `/healthz` | `GET` | 系統健康狀態 (`{"status": "healthy"}`) | **K8s Liveness/Readiness Probe** |
| `/status` | `GET` | 顯示當前伺服器主機名稱 (Hostname) 與 IP | **K8s 負載平衡 Demo** |
| `/webhook/github` | `POST` | 接收 GitHub 密鑰認證並於背景執行部署 | **VM 程式碼自動更新** |

---

## 🔄 需求 2：GitHub Webhook 自動更新設定 (VM)

本專案實作了 **HMAC SHA-256 簽章驗證**，能確保只有您指定的 GitHub 專案能觸發部署。

### 步驟 1：在 VM 設定環境變數
編輯 `.env` 檔案或在 `docker-compose.yml` 中設定您的 Webhook Secret：
```yaml
environment:
  - GITHUB_WEBHOOK_SECRET=my_super_secure_secret_123
```

### 步驟 2：在 GitHub 專案設定 Webhook
1. 前往您的 GitHub Repository -> **Settings** -> **Webhooks** -> **Add webhook**。
2. **Payload URL**: `http://<您的VM外網IP>/webhook/github`
3. **Content type**: `application/json`
4. **Secret**: 輸入您剛才設定的 `my_super_secure_secret_123`
5. **Which events**: 選擇 `Just the push event.`
6. 點擊 **Add webhook**。

### 步驟 3：部署腳本 (`deploy.sh`) 的運作邏輯
當您推送程式碼到 GitHub 時：
1. GitHub 發送 `POST` 請求到 `/webhook/github`。
2. FastAPI 驗證 `X-Hub-Signature-256` 簽章。
3. 驗證通過後，在**背景**執行 `./deploy.sh`：
    * 執行 `git pull origin main` 獲取最新程式碼。
    * 執行 `docker compose up -d --build` 自動重構並重啟容器。
    * *註：背景執行可確保 GitHub Webhook 立即收到 `200 OK` 回應，避免連線逾時。*

---

## ☸️ 需求 3：GKE (Kubernetes) Demo 指南與 YAML

這個專案的設計非常適合在 GKE 上進行 K8s 特性展示。以下為您整理的 GKE 部署步驟與 YAML 範本：

### 1. 建立 Kubernetes 部署設定 (`k8s-demo.yaml`)

建立一個名為 `k8s-demo.yaml` 的檔案並填入以下內容：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fastapi-nginx-demo
  labels:
    app: fastapi-nginx-demo
spec:
  replicas: 3 # 啟動 3 個 Pod 複本來展示負載平衡
  selector:
    matchLabels:
      app: fastapi-nginx-demo
  template:
    metadata:
      labels:
        app: fastapi-nginx-demo
    spec:
      containers:
      # 1. FastAPI 容器
      - name: fastapi-app
        image: <您的容器映像檔路徑> # 例如 gcr.io/your-project/fastapi-app:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8000
        # 設定 K8s 存活與就緒探針，指向健康檢查路由
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /healthz
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        env:
        - name: APP_ENV
          value: "production"
        - name: APP_VERSION
          value: "v1.0.0-gke"

---
apiVersion: v1
kind: Service
metadata:
  name: fastapi-nginx-service
spec:
  type: LoadBalancer # 建立雲端負載平衡器，配發外部 IP
  ports:
  - port: 80
    targetPort: 8000 # 如果走 GKE，可以直接將外部 Port 80 轉導給 FastAPI 的 8000
  selector:
    app: fastapi-nginx-demo
```

### 2. 在 GKE 叢集中部署
```bash
# 部署至 K8s
kubectl apply -f k8s-demo.yaml

# 查看外部 IP 配發狀態 (等待 EXTERNAL-IP 出現)
kubectl get service fastapi-nginx-service -w
```

### 3. 如何進行精彩的 K8s 功能 Demo？

#### 💡 Demo A：負載平衡 (Load Balancing) 展示
1. 瀏覽 `http://<GKE-EXTERNAL-IP>/status`。
2. 連續**強制重新整理網頁** (F5 / Ctrl+F5) 或在終端機執行：
   ```bash
   while true; do curl -s http://<GKE-EXTERNAL-IP>/status | grep hostname; sleep 1; done
   ```
3. **效果**：您會看見輸出的 `hostname` 在不同的 Pod 名稱（例如：`fastapi-nginx-demo-xxxx-yyyy`）之間輪詢切換。這證明了 K8s Service 正在完美地將流量負載平衡至 3 個 Pod！

#### 💡 Demo B：自癒能力 (Self-Healing) 展示
1. 藉由 `/healthz` 路由，K8s 隨時監控 Pod 狀態。
2. 嘗試刪除其中一個 Pod 或手動進入容器使 API 故障，K8s 會偵測到不健康並在幾秒鐘內**自動重啟或重建**該 Pod，保障服務 100% 存活。

#### 💡 Demo C：滾動更新 (Rolling Update) 不中斷服務
1. 修改 `k8s-demo.yaml` 中的 `APP_VERSION` 環境變數為 `v1.1.0-gke`。
2. 執行 `kubectl apply -f k8s-demo.yaml`。
3. 同時持續執行 `curl -s http://<GKE-EXTERNAL-IP>/status` 監控。
4. **效果**：您會看見部分 Pod 顯示 `v1.0.0`，部分顯示 `v1.1.0`，期間 **完全沒有任何一個 request 失敗**（零停機時間 Zero-Downtime），最終所有 Pod 順利平滑升級！

123
