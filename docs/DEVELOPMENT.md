# Development & Deployment Guide

## Quick Start (Local Development)

### Prerequisites
- Python 3.10
- ViennaRNA installed (`brew install brewsci/bio/viennarna` on macOS)
- Git LFS installed (`brew install git-lfs`)

### First-time Setup
```bash
git lfs install
git lfs pull
python3.10 -m venv venv310
source venv310/bin/activate
pip install -r webapp/requirements.txt
```

### Run Locally
```bash
source venv310/bin/activate
python -m uvicorn webapp.app.main:app --port 7860 --reload
```

Visit: http://localhost:7860

## Docker Development

### Build & Run
```bash
docker compose up --build
```

### Production-like Run
```bash
docker compose -f docker-compose.prod.yml up
```

## Deployment to Hugging Face Spaces

### Automatic (CI/CD) - Recommended
Push to `main` branch triggers automatic deployment:
```bash
git push origin main
```

The GitHub Action will:
1. Run tests
2. Push to HF Spaces (https://huggingface.co/spaces/sachin1801/splicing-predictor)

### Manual Deployment
```bash
git push hf main
```

### Required Secrets
- `HF_TOKEN` - Hugging Face access token with write permissions

## Troubleshooting

### "file signature not found" error
Run: `git lfs pull`

### Port mismatch (Shiny apps show "connection failed")
Use port 7860: `python -m uvicorn webapp.app.main:app --port 7860`

### Database corruption
Delete and restart: `rm webapp/splicing.db`
