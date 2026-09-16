# Neuvon Dashboard — Deployment Guide

> Complete step-by-step guide to deploy the Neuvon AI Calling Dashboard (frontend + backend) on any Linux server (Ubuntu/Debian).

## Architecture Overview

```
Linux Server
│
├── Nginx (reverse proxy)                → port 80
│   ├── /                → React static files (frontend)
│   └── /api/            → FastAPI backend (port 8001)
│
├── FastAPI (Gunicorn + Uvicorn)         → port 8001
├── Celery Worker                        → background tasks (sheet sync, campaigns)
├── Celery Beat                          → scheduled tasks
└── Redis                                → port 6379 (Celery broker + cache)
```

---

## Step 1 — Install System Dependencies

```bash
# Update packages
sudo apt update && sudo apt upgrade -y

# Install Python 3.12+, pip, venv
sudo apt install -y python3 python3-pip python3-venv

# Install Node.js 20.x (for building frontend)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Install Nginx
sudo apt install -y nginx

# Install Redis
sudo apt install -y redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Verify installations
python3 --version   # Should be 3.12+
node --version      # Should be 20.x
nginx -v            # Should be 1.x
redis-cli ping      # Should return PONG
```

---

## Step 2 — Clone the Repository

```bash
cd ~
git clone https://github.com/praveen88p/neuvon-ai-calling-platform.git dashboard
cd dashboard
```

---

## Step 3 — Set Up the Backend

### 3a. Create Python virtual environment

```bash
cd ~/dashboard/backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3b. Install Gunicorn (production server)

```bash
pip install gunicorn
```

### 3c. Create the `.env` file

```bash
nano ~/dashboard/backend/.env
```

```env
# ── InsForge (Auth + DB + Storage) ──────────────────
INSFORGE_URL=https://your-project.insforge.co
INSFORGE_ANON_KEY=<your-anon-key>
INSFORGE_SERVICE_KEY=<your-service-key>

# ── Dograh (Voice Orchestration) ────────────────────
DOGRAH_BASE_URL=<your-dograh-url>
DOGRAH_API_KEY=<your-dograh-api-key>

# ── Security ────────────────────────────────────────
# Generate with: openssl rand -hex 32
SECRET_KEY=<generated-64-char-hex-string>

# ── Redis (Celery broker + cache) ───────────────────
REDIS_URL=redis://localhost:6379/0

# ── CORS ────────────────────────────────────────────
# Add your server's public IP or domain
CORS_ORIGINS=["http://<YOUR-SERVER-IP>","https://app.neuvonsoftware.com"]

# ── Public URL (used for webhook callbacks) ─────────
BACKEND_PUBLIC_URL=http://<YOUR-SERVER-IP>

# ── Razorpay (Billing) ─────────────────────────────
RAZORPAY_KEY_ID=<your-razorpay-key>
RAZORPAY_KEY_SECRET=<your-razorpay-secret>
RAZORPAY_WEBHOOK_SECRET=<your-webhook-secret>

# ── PostHog (Analytics) ────────────────────────────
POSTHOG_API_KEY=<your-posthog-key>
POSTHOG_HOST=https://us.i.posthog.com

# ── Webhook ────────────────────────────────────────
WEBHOOK_SECRET=<your-webhook-signing-secret>

# ── Environment ────────────────────────────────────
ENVIRONMENT=production

# ── Sentry (Error Tracking — optional) ─────────────
# SENTRY_DSN=https://xxx@sentry.io/xxx
```

> [!IMPORTANT]
> If Dograh is running on the **same server**, set `REDIS_URL=redis://localhost:6379/1` (database 1) to avoid conflicts with Dograh's Redis (database 0).

### 3d. Test the backend starts

```bash
source ~/dashboard/backend/venv/bin/activate
cd ~/dashboard/backend
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

Verify: `curl http://localhost:8001/api/v1/health` — should return JSON.
Press `Ctrl+C` to stop.

---

## Step 4 — Build the Frontend

```bash
cd ~/dashboard/frontend
npm ci
npm run build
```

The built files will be in `~/dashboard/frontend/dist/`.

---

## Step 5 — Set Up Systemd Services

> [!NOTE]
> Replace `<YOUR-USERNAME>` with your actual Linux username (e.g. `ubuntu`, `ec2-user`, `admin`).
> Find it by running: `whoami`

### 5a. FastAPI (Gunicorn + Uvicorn)

```bash
sudo nano /etc/systemd/system/neuvon-api.service
```

```ini
[Unit]
Description=Neuvon Dashboard API
After=network.target redis-server.service

[Service]
Type=simple
User=<YOUR-USERNAME>
WorkingDirectory=/home/<YOUR-USERNAME>/dashboard/backend
Environment="PATH=/home/<YOUR-USERNAME>/dashboard/backend/venv/bin"
ExecStart=/home/<YOUR-USERNAME>/dashboard/backend/venv/bin/gunicorn \
    app.main:app \
    --workers 2 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8001 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 5b. Celery Worker

```bash
sudo nano /etc/systemd/system/neuvon-celery-worker.service
```

```ini
[Unit]
Description=Neuvon Celery Worker
After=network.target redis-server.service

[Service]
Type=simple
User=<YOUR-USERNAME>
WorkingDirectory=/home/<YOUR-USERNAME>/dashboard/backend
Environment="PATH=/home/<YOUR-USERNAME>/dashboard/backend/venv/bin"
ExecStart=/home/<YOUR-USERNAME>/dashboard/backend/venv/bin/celery \
    -A app.tasks.sheet_tasks:celery worker \
    --loglevel=info \
    --concurrency=2
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 5c. Celery Beat (Scheduler)

```bash
sudo nano /etc/systemd/system/neuvon-celery-beat.service
```

```ini
[Unit]
Description=Neuvon Celery Beat Scheduler
After=network.target neuvon-celery-worker.service

[Service]
Type=simple
User=<YOUR-USERNAME>
WorkingDirectory=/home/<YOUR-USERNAME>/dashboard/backend
Environment="PATH=/home/<YOUR-USERNAME>/dashboard/backend/venv/bin"
ExecStart=/home/<YOUR-USERNAME>/dashboard/backend/venv/bin/celery \
    -A app.tasks.sheet_tasks:celery beat \
    --loglevel=info
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 5d. Enable and start all services

```bash
sudo systemctl daemon-reload

# Enable (auto-start on boot)
sudo systemctl enable neuvon-api neuvon-celery-worker neuvon-celery-beat

# Start all
sudo systemctl start neuvon-api neuvon-celery-worker neuvon-celery-beat

# Check status
sudo systemctl status neuvon-api neuvon-celery-worker neuvon-celery-beat
```

---

## Step 6 — Configure Nginx

```bash
sudo nano /etc/nginx/sites-available/neuvon
```

```nginx
server {
    listen 80;
    server_name _;

    # ── Frontend (React SPA) ──────────────────────────
    root /home/<YOUR-USERNAME>/dashboard/frontend/dist;
    index index.html;

    # SPA fallback — serve index.html for all non-file routes
    location / {
        try_files $uri $uri/ /index.html;
    }

    # ── Dashboard API (FastAPI on port 8001) ──────────
    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (for SSE/streaming if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts for long-running API calls
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }

    # ── Static assets caching ─────────────────────────
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2|woff|ttf)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

Enable and restart:

```bash
# Enable the site
sudo ln -sf /etc/nginx/sites-available/neuvon /etc/nginx/sites-enabled/neuvon

# Remove default site
sudo rm -f /etc/nginx/sites-enabled/default

# Test config
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

> [!IMPORTANT]
> Make sure your server's firewall / security group allows **port 80** (HTTP) inbound from `0.0.0.0/0`.

---

## Step 7 — Verify Deployment

```bash
# 1. Check all services are running
sudo systemctl status neuvon-api neuvon-celery-worker neuvon-celery-beat nginx

# 2. Test API directly
curl http://localhost:8001/api/v1/health

# 3. Test through Nginx
curl http://localhost/api/v1/health

# 4. Test frontend loads
curl -I http://localhost/
```

Then open in your browser: **`http://<YOUR-SERVER-IP>`**

---

## Useful Commands

### View logs

```bash
# API logs (live)
sudo journalctl -u neuvon-api -f --no-pager

# Celery worker logs
sudo journalctl -u neuvon-celery-worker -f --no-pager

# Celery beat logs
sudo journalctl -u neuvon-celery-beat -f --no-pager

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Restart services

```bash
# Restart everything
sudo systemctl restart neuvon-api neuvon-celery-worker neuvon-celery-beat

# Restart just the API
sudo systemctl restart neuvon-api
```

### Deploy updates (after `git push`)

```bash
cd ~/dashboard

# 1. Pull latest code
git pull origin main

# 2. Backend: reinstall deps + restart
cd backend
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart neuvon-api neuvon-celery-worker neuvon-celery-beat

# 3. Frontend: rebuild (Nginx picks it up automatically)
cd ../frontend
npm ci
npm run build

# Done!
```

---

## Port Map Summary

| Service | Port | Access |
|---------|------|--------|
| Nginx (frontend + API proxy) | **80** | `http://<YOUR-SERVER-IP>` |
| Dashboard API (FastAPI) | 8001 | Internal only (proxied via Nginx) |
| Celery Worker | — | Background process |
| Celery Beat | — | Scheduler process |
| Redis | 6379 | Internal only |
