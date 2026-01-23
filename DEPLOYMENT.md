# Deployment Documentation

This document describes the Docker containerization and CI/CD pipeline setup for the Interpretable Splicing Model webapp.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Decisions](#architecture-decisions)
3. [Files Created](#files-created)
4. [How Each Component Works](#how-each-component-works)
5. [Deployment Flow](#deployment-flow)
6. [Configuration Reference](#configuration-reference)
7. [Common Modifications](#common-modifications)
8. [Next Steps](#next-steps)
9. [Troubleshooting](#troubleshooting)

---

## Overview

The webapp is containerized using Docker for deployment on Ubuntu 24.04 VMs with Apache as a reverse proxy. The CI/CD pipeline uses GitHub Actions to automatically:

- Run tests on every push/PR
- Build and push Docker images
- Deploy to test environment on `main` branch pushes
- Deploy to production on version tags (e.g., `v1.0.0`)

### Key Points

- **No GPU required**: The TensorFlow model runs on CPU only
- **SQLite database**: Persisted via Docker volumes
- **Image promotion**: Test images are promoted to production (not rebuilt)
- **WebSocket support**: Apache configured for PyShiny interactive visualizations

---

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| CI/CD Platform | GitHub Actions | Native GitHub integration, free for public repos |
| Container Registry | Self-hosted (configurable) | Flexibility for on-premise or cloud registries |
| Web Server | Apache Reverse Proxy | Required by deployment environment (Ubuntu VMs) |
| Python Version | 3.10 | Required for TensorFlow 2.15 (Keras 2 compatibility) |
| Base Image | `python:3.10-slim-bookworm` | Debian-based, includes ViennaRNA package |
| Branch Strategy | `main` → test, tags → prod | Clear separation of environments |
| Secrets Management | GitHub Secrets + env files | Secure CI/CD + runtime configuration |
| Database Persistence | Docker named volumes | Survives container restarts/updates |

---

## Files Created

### Docker Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Multi-stage build for the webapp container |
| `.dockerignore` | Excludes unnecessary files from build context |
| `docker-compose.yml` | Local development configuration |
| `docker-compose.prod.yml` | Production deployment template |

### GitHub Actions Workflows

| File | Purpose |
|------|---------|
| `.github/workflows/ci.yml` | Runs tests and builds Docker image on push/PR |
| `.github/workflows/deploy-test.yml` | Deploys to test server on `main` push |
| `.github/workflows/deploy-prod.yml` | Deploys to production on version tags |

### Deployment Configuration

| File | Purpose |
|------|---------|
| `deploy/apache-site.conf` | Apache virtual host configuration |
| `deploy/server-setup.sh` | Server initialization script for Ubuntu 24.04 |

---

## How Each Component Works

### 1. Dockerfile

```
Location: /Dockerfile
```

**What it does:**
- Uses multi-stage build to minimize final image size
- Stage 1 (builder): Compiles Python wheels from requirements
- Stage 2 (production): Installs ViennaRNA and pre-built wheels

**Key sections:**

```dockerfile
# Stage 1: Build wheels
FROM python:3.10-slim-bookworm AS builder
# Installs build-essential for compiling C extensions
# Creates wheels in /app/wheels

# Stage 2: Production image
FROM python:3.10-slim-bookworm
# Installs vienna-rna system package
# Copies and installs pre-built wheels (faster, smaller)
# Copies application code: webapp/, figures/, output/, data/
# Creates non-root user 'appuser' for security
# Exposes port 8000
# Configures health check against /api/health
# Runs uvicorn on 0.0.0.0:8000
```

**What to change if:**

| Scenario | What to modify |
|----------|----------------|
| Add system dependency | Add to `apt-get install` in Stage 2 |
| Add Python dependency | Add to `webapp/requirements.txt` (wheels auto-built) |
| Change port | Modify `EXPOSE` and `CMD` uvicorn port |
| Add more app directories | Add additional `COPY` statements |
| Increase health check timeout | Modify `HEALTHCHECK` parameters |

---

### 2. .dockerignore

```
Location: /.dockerignore
```

**What it does:**
- Excludes files from Docker build context to speed up builds and reduce image size
- Prevents sensitive files (`.env`, credentials) from being included

**What to change if:**

| Scenario | What to modify |
|----------|----------------|
| Include a previously ignored file | Remove from `.dockerignore` |
| Exclude additional files | Add pattern to `.dockerignore` |
| Include specific markdown file | Add exception like `!filename.md` |

---

### 3. docker-compose.yml (Local Development)

```
Location: /docker-compose.yml
```

**What it does:**
- Builds the Docker image locally
- Mounts `./webapp` as read-only volume for code changes
- Exposes port 8000 on localhost
- Creates `db-data` volume for database persistence

**Usage:**
```bash
# Build and start
docker-compose up --build

# Start in background
docker-compose up -d

# Stop
docker-compose down

# View logs
docker-compose logs -f
```

**What to change if:**

| Scenario | What to modify |
|----------|----------------|
| Change local port | Modify `ports: - "8000:8000"` to `"NEW_PORT:8000"` |
| Add environment variable | Add under `environment:` section |
| Mount additional directory | Add under `volumes:` section |
| Enable debug mode | Set `DEBUG=true` in environment |

---

### 4. docker-compose.prod.yml (Production)

```
Location: /docker-compose.prod.yml
```

**What it does:**
- Pulls image from container registry (not builds locally)
- Binds only to localhost (Apache proxies external traffic)
- Uses external `splicing-db` volume for database
- Loads secrets from `.env.production` file
- Configures log rotation (10MB max, 3 files)
- Auto-restarts on failure (`unless-stopped`)

**Key differences from development:**
- Uses pre-built image from registry
- Port bound to `127.0.0.1` only (not exposed externally)
- Uses external volume (must be created manually)
- Loads production environment file

**Environment variables required in `.env.production`:**
```bash
# Create on server at /opt/splicing-model/.env.production
DEBUG=false
# Add any other production-specific settings
```

**What to change if:**

| Scenario | What to modify |
|----------|----------------|
| Change registry URL | Set `REGISTRY_URL` environment variable |
| Change image tag | Set `IMAGE_TAG` environment variable |
| Add production secret | Add to `.env.production` file on server |
| Change log retention | Modify `logging.options` section |
| Change volume mount path | Modify `volumes:` section |

---

### 5. CI Workflow (.github/workflows/ci.yml)

```
Location: /.github/workflows/ci.yml
```

**What it does:**
- Triggers on push to `main`/`develop` and PRs to `main`
- **Test job**: Installs dependencies, runs pytest
- **Build job**: Builds Docker image, runs container health check

**Workflow steps:**

```
Push/PR → Test Job → Build Job
              ↓           ↓
         Run pytest   Build image
                          ↓
                     Start container
                          ↓
                     Health check
```

**What to change if:**

| Scenario | What to modify |
|----------|----------------|
| Add branch to CI | Add to `branches:` list under `on.push` |
| Add test command | Modify the `Run tests` step |
| Change Python version | Modify `python-version` in setup-python |
| Add CI environment variable | Add `env:` section to job or step |
| Skip tests for certain paths | Add `paths-ignore:` under `on.push` |

---

### 6. Test Deployment Workflow (.github/workflows/deploy-test.yml)

```
Location: /.github/workflows/deploy-test.yml
```

**What it does:**
- Triggers on push to `main` branch only
- Builds Docker image and pushes to registry with tags:
  - `<commit-sha>` (for traceability)
  - `test-latest` (for deployment)
- SSHs into test server and deploys new image

**Workflow steps:**

```
Push to main → Build & Push → Deploy to Test
                    ↓              ↓
              Push to registry   SSH to server
                    ↓              ↓
              Tags: sha,       docker pull
              test-latest      docker-compose up
```

**Required GitHub Secrets:**
- `REGISTRY_URL` - Container registry URL
- `REGISTRY_USERNAME` - Registry login username
- `REGISTRY_PASSWORD` - Registry login password
- `TEST_SERVER_HOST` - Test server hostname/IP
- `TEST_SERVER_USER` - SSH username
- `TEST_SERVER_SSH_KEY` - SSH private key

**What to change if:**

| Scenario | What to modify |
|----------|----------------|
| Change deployment directory | Modify `cd /opt/splicing-model` in SSH script |
| Add pre-deployment step | Add commands before `docker pull` in script |
| Change image name | Modify `IMAGE_NAME` env variable |
| Add deployment notification | Add step after deploy (e.g., Slack webhook) |
| Skip deployment for certain files | Add `paths-ignore:` under `on.push` |

---

### 7. Production Deployment Workflow (.github/workflows/deploy-prod.yml)

```
Location: /.github/workflows/deploy-prod.yml
```

**What it does:**
- Triggers on version tags (e.g., `v1.0.0`, `v2.3.1`)
- **Does NOT rebuild** - promotes test-latest image to production
- Tags image with version number and `prod-latest`
- SSHs into production server and deploys

**Image promotion flow:**

```
test-latest → v1.0.0 (versioned)
            → prod-latest (deployment tag)
```

**Why image promotion?**
- Ensures production runs exact same image as tested
- Faster deployments (no rebuild)
- Version tags provide rollback points

**Required GitHub Secrets:**
- Same registry secrets as test deployment
- `PROD_SERVER_HOST` - Production server hostname/IP
- `PROD_SERVER_USER` - SSH username
- `PROD_SERVER_SSH_KEY` - SSH private key

**What to change if:**

| Scenario | What to modify |
|----------|----------------|
| Change version tag pattern | Modify `tags:` pattern under `on.push` |
| Add manual approval | Already uses `environment: production` (configure in GitHub) |
| Rebuild instead of promote | Replace retag steps with build-push-action |
| Add rollback capability | Store previous IMAGE_TAG before updating |

---

### 8. Apache Configuration (deploy/apache-site.conf)

```
Location: /deploy/apache-site.conf
```

**What it does:**
- Configures Apache as reverse proxy to the Docker container
- Forwards HTTP requests to `127.0.0.1:8000`
- Handles WebSocket upgrades for PyShiny
- Logs to `/var/log/apache2/splicing-*.log`

**Key sections:**

```apache
# Proxy all requests to Docker container
ProxyPass / http://127.0.0.1:8000/
ProxyPassReverse / http://127.0.0.1:8000/

# WebSocket support (required for PyShiny)
RewriteCond %{HTTP:Upgrade} websocket [NC]
RewriteRule ^/?(.*) "ws://127.0.0.1:8000/$1" [P,L]
```

**Installation on server:**
```bash
# Copy config
sudo cp deploy/apache-site.conf /etc/apache2/sites-available/splicing.conf

# Edit ServerName
sudo nano /etc/apache2/sites-available/splicing.conf
# Change ${SERVER_NAME} to your actual domain

# Enable site
sudo a2ensite splicing
sudo systemctl reload apache2
```

**What to change if:**

| Scenario | What to modify |
|----------|----------------|
| Change domain name | Replace `${SERVER_NAME}` with actual domain |
| Enable HTTPS | Uncomment the SSL VirtualHost section |
| Change container port | Update `127.0.0.1:8000` to new port |
| Add custom headers | Add `Header set` directives |
| Serve at subpath (e.g., /app) | Modify ProxyPass paths |

---

### 9. Server Setup Script (deploy/server-setup.sh)

```
Location: /deploy/server-setup.sh
```

**What it does:**
- Installs Docker using official install script
- Installs Docker Compose plugin
- Installs Apache with required modules
- Creates `/opt/splicing-model` directory
- Creates `splicing-db` Docker volume

**Run on server:**
```bash
# Copy script to server
scp deploy/server-setup.sh user@server:/tmp/

# SSH to server and run
ssh user@server
bash /tmp/server-setup.sh

# Log out and back in (for docker group)
exit
ssh user@server
```

**What to change if:**

| Scenario | What to modify |
|----------|----------------|
| Change app directory | Modify `/opt/splicing-model` paths |
| Change volume name | Modify `docker volume create` command |
| Add additional packages | Add `apt-get install` commands |
| Skip Apache installation | Remove Apache section |

---

### 10. Health Endpoint (webapp/app/api/routes.py)

```
Location: /webapp/app/api/routes.py:55-77
```

**What it does:**
- Provides `/api/health` endpoint for container orchestration
- Checks if TensorFlow model is loaded
- Checks if database connection works
- Returns `healthy` or `degraded` status

**Response format:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "model_loaded": true,
  "database_connected": true
}
```

**Used by:**
- Docker HEALTHCHECK command
- Load balancers
- Monitoring systems

**What to change if:**

| Scenario | What to modify |
|----------|----------------|
| Add health check | Add check in `health_check()` function |
| Change response fields | Modify `HealthResponse` schema |
| Add external service check | Add try/except block similar to db check |

---

## Deployment Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        DEVELOPMENT                               │
├─────────────────────────────────────────────────────────────────┤
│  Developer pushes code to feature branch                        │
│       ↓                                                         │
│  Creates Pull Request to main                                   │
│       ↓                                                         │
│  CI runs: tests + Docker build (ci.yml)                        │
│       ↓                                                         │
│  PR merged to main                                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      TEST DEPLOYMENT                             │
├─────────────────────────────────────────────────────────────────┤
│  Push to main triggers deploy-test.yml                          │
│       ↓                                                         │
│  Build Docker image                                             │
│       ↓                                                         │
│  Push to registry: <sha>, test-latest                          │
│       ↓                                                         │
│  SSH to test server                                             │
│       ↓                                                         │
│  docker pull → docker-compose up                                │
│       ↓                                                         │
│  Manual QA testing on test environment                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   PRODUCTION DEPLOYMENT                          │
├─────────────────────────────────────────────────────────────────┤
│  Developer creates version tag: git tag v1.0.0                  │
│       ↓                                                         │
│  Push tag: git push origin v1.0.0                               │
│       ↓                                                         │
│  deploy-prod.yml triggered                                      │
│       ↓                                                         │
│  Pull test-latest, retag as v1.0.0 + prod-latest               │
│       ↓                                                         │
│  Push production tags to registry                               │
│       ↓                                                         │
│  SSH to production server                                       │
│       ↓                                                         │
│  docker pull → docker-compose up                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Configuration Reference

### GitHub Secrets Required

Configure in: Repository → Settings → Secrets and variables → Actions

| Secret | Description | Example |
|--------|-------------|---------|
| `REGISTRY_URL` | Container registry URL | `registry.example.com` |
| `REGISTRY_USERNAME` | Registry login username | `deploy-user` |
| `REGISTRY_PASSWORD` | Registry login password | `***` |
| `TEST_SERVER_HOST` | Test server IP/hostname | `test.example.com` |
| `TEST_SERVER_USER` | SSH username for test | `deploy` |
| `TEST_SERVER_SSH_KEY` | SSH private key for test | `-----BEGIN OPENSSH...` |
| `PROD_SERVER_HOST` | Production server IP/hostname | `prod.example.com` |
| `PROD_SERVER_USER` | SSH username for prod | `deploy` |
| `PROD_SERVER_SSH_KEY` | SSH private key for prod | `-----BEGIN OPENSSH...` |

### GitHub Environments (Optional)

Configure in: Repository → Settings → Environments

**test environment:**
- No special configuration needed
- Deploys automatically on main push

**production environment:**
- Enable "Required reviewers" for manual approval
- Add deployment protection rules as needed

### Server Directory Structure

```
/opt/splicing-model/
├── docker-compose.prod.yml    # Copied from repo
├── .env.production            # Created manually with secrets
└── (container runs here)

Docker volumes:
└── splicing-db                # SQLite database persistence
```

---

## Common Modifications

### Adding a New Environment Variable

1. **For local development:**
   ```yaml
   # docker-compose.yml
   environment:
     - NEW_VAR=value
   ```

2. **For production:**
   ```bash
   # On server: /opt/splicing-model/.env.production
   NEW_VAR=production_value
   ```

3. **For CI/CD:**
   ```yaml
   # .github/workflows/*.yml
   env:
     NEW_VAR: ${{ secrets.NEW_VAR }}
   ```

### Changing the Port

1. **Dockerfile:**
   ```dockerfile
   EXPOSE 9000
   CMD ["python", "-m", "uvicorn", "...", "--port", "9000"]
   ```

2. **docker-compose.yml:**
   ```yaml
   ports:
     - "9000:9000"
   ```

3. **docker-compose.prod.yml:**
   ```yaml
   ports:
     - "127.0.0.1:9000:9000"
   ```

4. **Apache config:**
   ```apache
   ProxyPass / http://127.0.0.1:9000/
   ```

5. **Health check in Dockerfile:**
   ```dockerfile
   CMD python -c "import httpx; httpx.get('http://localhost:9000/api/health')"
   ```

### Adding a New Python Dependency

1. Add to `webapp/requirements.txt`
2. Rebuild Docker image: `docker-compose build`
3. Commit and push - CI/CD will build new image

### Adding a System Dependency

1. **Dockerfile (Stage 2):**
   ```dockerfile
   RUN apt-get update && apt-get install -y --no-install-recommends \
       vienna-rna \
       new-package \
       && rm -rf /var/lib/apt/lists/*
   ```

### Changing the Container Registry

1. **Update GitHub Secrets:**
   - `REGISTRY_URL` → new registry URL
   - `REGISTRY_USERNAME` → new credentials
   - `REGISTRY_PASSWORD` → new credentials

2. **Update server `.env.production`:**
   ```bash
   REGISTRY_URL=new-registry.example.com
   ```

### Adding SSL/HTTPS

1. **Obtain SSL certificate** (e.g., Let's Encrypt)

2. **Update Apache config:**
   ```apache
   # Uncomment the HTTPS VirtualHost section in apache-site.conf
   # Update certificate paths
   SSLCertificateFile /etc/ssl/certs/your-domain.crt
   SSLCertificateKeyFile /etc/ssl/private/your-domain.key
   ```

3. **Enable SSL module:**
   ```bash
   sudo a2enmod ssl
   sudo systemctl reload apache2
   ```

### Rolling Back Production

```bash
# SSH to production server
ssh deploy@prod.example.com

# Pull previous version
docker pull registry.example.com/splicing-model:v1.0.0

# Deploy previous version
cd /opt/splicing-model
IMAGE_TAG=v1.0.0 docker-compose -f docker-compose.prod.yml up -d
```

---

## Next Steps

### 1. Configure GitHub Secrets

**Priority: Required before first deployment**

Go to your GitHub repository → Settings → Secrets and variables → Actions, and add all the secrets listed in [Configuration Reference](#github-secrets-required).

For SSH keys, generate a dedicated deployment key:
```bash
ssh-keygen -t ed25519 -C "github-deploy" -f deploy_key
# Add deploy_key.pub to server's ~/.ssh/authorized_keys
# Add deploy_key (private) as GitHub secret
```

### 2. Set Up Container Registry

**Priority: Required before first deployment**

Options:
- **GitHub Container Registry (ghcr.io)**: Free for public repos
- **Docker Hub**: Free tier available
- **Self-hosted**: Harbor, GitLab Registry, etc.

Update `REGISTRY_URL` secret accordingly.

### 3. Prepare Test Server

**Priority: Required for test deployments**

```bash
# SSH to test server
ssh user@test.example.com

# Run setup script
bash /path/to/server-setup.sh

# Copy production compose file
scp docker-compose.prod.yml user@test.example.com:/opt/splicing-model/

# Create environment file
ssh user@test.example.com
echo "DEBUG=false" > /opt/splicing-model/.env.production

# Configure Apache
sudo cp /path/to/apache-site.conf /etc/apache2/sites-available/splicing.conf
sudo nano /etc/apache2/sites-available/splicing.conf  # Set ServerName
sudo a2ensite splicing
sudo systemctl reload apache2
```

### 4. Prepare Production Server

**Priority: Required for production deployments**

Same steps as test server, on the production machine.

### 5. Configure GitHub Environments (Optional)

**Priority: Recommended for production safety**

Go to Repository → Settings → Environments:
- Create `test` environment (auto-deploy)
- Create `production` environment with required reviewers

### 6. Test the Pipeline

**Priority: Verify everything works**

```bash
# Test local Docker build
docker-compose up --build
curl http://localhost:8000/api/health

# Test CI pipeline
git checkout -b test-ci
git commit --allow-empty -m "Test CI pipeline"
git push origin test-ci
# Create PR and verify CI passes

# Test deployment
git checkout main
git merge test-ci
git push origin main
# Verify test deployment

# Test production deployment
git tag v0.1.0
git push origin v0.1.0
# Verify production deployment
```

### 7. Set Up Monitoring (Optional)

**Priority: Recommended for production**

- Configure uptime monitoring for `/api/health`
- Set up log aggregation (e.g., Loki, ELK)
- Add alerting for failed deployments

### 8. Configure SSL/HTTPS

**Priority: Required for production**

See [Adding SSL/HTTPS](#adding-sslhttps) in Common Modifications.

---

## Troubleshooting

### Container won't start

```bash
# Check container logs
docker-compose logs webapp

# Check if port is in use
sudo lsof -i :8000

# Check container status
docker ps -a
```

### Health check failing

```bash
# Test health endpoint manually
docker exec <container_id> python -c "import httpx; print(httpx.get('http://localhost:8000/api/health').json())"

# Check if model loaded
docker logs <container_id> | grep -i model
```

### CI pipeline failing

1. Check GitHub Actions logs for specific error
2. Common issues:
   - Missing secrets
   - ViennaRNA installation failure
   - Test failures

### Deployment SSH failing

```bash
# Test SSH connection manually
ssh -i /path/to/key deploy@server.example.com

# Check key permissions
chmod 600 /path/to/key

# Verify key is in authorized_keys on server
```

### Apache proxy not working

```bash
# Check Apache status
sudo systemctl status apache2

# Check Apache error logs
sudo tail -f /var/log/apache2/splicing-error.log

# Verify modules enabled
sudo apache2ctl -M | grep -E "proxy|rewrite"

# Test local connection
curl http://127.0.0.1:8000/api/health
```

### Database not persisting

```bash
# Check volume exists
docker volume ls | grep splicing

# Inspect volume
docker volume inspect splicing-db

# Verify mount in container
docker inspect <container_id> | grep -A5 Mounts
```

---

## File Quick Reference

| Need to... | Edit this file |
|------------|----------------|
| Change Python dependencies | `webapp/requirements.txt` |
| Change system packages | `Dockerfile` (Stage 2 apt-get) |
| Change local dev settings | `docker-compose.yml` |
| Change production settings | `docker-compose.prod.yml` + `.env.production` |
| Change CI test commands | `.github/workflows/ci.yml` |
| Change test deploy process | `.github/workflows/deploy-test.yml` |
| Change prod deploy process | `.github/workflows/deploy-prod.yml` |
| Change Apache/web server | `deploy/apache-site.conf` |
| Change server setup | `deploy/server-setup.sh` |
| Change health check logic | `webapp/app/api/routes.py` |
