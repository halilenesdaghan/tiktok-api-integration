# Makefile for TikTok API Integration

.PHONY: help install dev test lint format clean docker-up docker-down migrate

# Default target
help:
	@echo "TikTok API Integration - Development Commands"
	@echo "============================================"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make install      - Install dependencies"
	@echo "  make setup        - Complete project setup"
	@echo ""
	@echo "Development:"
	@echo "  make dev          - Run development server"
	@echo "  make test         - Run tests with coverage"
	@echo "  make lint         - Run linting checks"
	@echo "  make format       - Format code with black"
	@echo "  make clean        - Clean cache and temp files"
	@echo ""
	@echo "Database:"
	@echo "  make migrate      - Run database migrations"
	@echo "  make migration    - Create new migration"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up    - Start all services with Docker"
	@echo "  make docker-down  - Stop all Docker services"
	@echo "  make docker-build - Build Docker images"
	@echo ""

# Installation
install:
	pip install --upgrade pip
	pip install -r requirements.txt

setup:
	chmod +x scripts/setup.sh
	./scripts/setup.sh

# Development
dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Testing
test:
	pytest tests/ -v --cov=app --cov-report=html --cov-report=term

test-watch:
	ptw tests/ -- -v

# Code quality
lint:
	pylint app --exit-zero
	mypy app --ignore-missing-imports

format:
	black app tests
	isort app tests

check: lint
	black --check app tests
	isort --check-only app tests

# Database
migrate:
	alembic upgrade head

migration:
	@read -p "Enter migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

migrate-down:
	alembic downgrade -1

# Docker
docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-build:
	docker-compose build

docker-logs:
	docker-compose logs -f

docker-dev:
	docker-compose --profile development up -d

docker-prod:
	docker-compose --profile production up -d

# Cleaning
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	rm -f .coverage
	rm -rf build/
	rm -rf dist/

# Environment
env:
	cp .env.example .env
	@echo "Created .env file. Please update with your credentials."

# Redis
redis-start:
	redis-server --daemonize yes

redis-stop:
	redis-cli shutdown

redis-cli:
	redis-cli

# PostgreSQL
db-create:
	createdb tiktok_api_db

db-drop:
	dropdb tiktok_api_db --if-exists

db-reset: db-drop db-create migrate

# Shortcuts
run: dev
t: test
f: format
l: lint
m: migrate