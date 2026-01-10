# Makefile for Splicing Predictor Web Application

.PHONY: help install dev run test clean lint format docker-build docker-run

# Default target
help:
	@echo "Splicing Predictor Web Application"
	@echo ""
	@echo "Usage:"
	@echo "  make install    Install dependencies"
	@echo "  make dev        Run development server with hot reload"
	@echo "  make run        Run production server"
	@echo "  make test       Run tests"
	@echo "  make lint       Run linters"
	@echo "  make format     Format code"
	@echo "  make clean      Remove cache files"
	@echo "  make docker-build  Build Docker image"
	@echo "  make docker-run    Run Docker container"

# Install dependencies
install:
	pip install -r requirements.txt

# Run development server with auto-reload
dev:
	cd .. && PYTHONPATH=. uvicorn webapp.app.main:app --reload --host 0.0.0.0 --port 8000

# Run production server
run:
	cd .. && PYTHONPATH=. uvicorn webapp.app.main:app --host 0.0.0.0 --port 8000

# Run tests
test:
	cd .. && PYTHONPATH=. pytest webapp/tests -v

# Run linters
lint:
	ruff check .
	mypy app/

# Format code
format:
	ruff format .
	isort .

# Clean cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -f splicing.db 2>/dev/null || true

# Build Docker image
docker-build:
	docker build -t splicing-predictor .

# Run Docker container
docker-run:
	docker run -p 8000:8000 splicing-predictor

# Initialize database
init-db:
	cd .. && PYTHONPATH=. python -c "from webapp.app.database import init_db; init_db()"

# Extract example sequences from test data
extract-examples:
	cd .. && PYTHONPATH=. python webapp/scripts/extract_examples.py
