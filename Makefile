.PHONY: help build up down restart logs clean backup restore monitor

help: ## Show this help message
	@echo "OCR Admission Forms - Deployment Commands"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

build: ## Build Docker images
	docker-compose build

up: ## Start all services
	docker-compose up -d

down: ## Stop all services
	docker-compose down

restart: ## Restart all services
	docker-compose restart

logs: ## View logs from all services
	docker-compose logs -f

logs-backend: ## View backend logs
	docker-compose logs -f backend

logs-frontend: ## View frontend logs
	docker-compose logs -f frontend

logs-db: ## View database logs
	docker-compose logs -f postgres

clean: ## Remove containers, volumes, and images
	docker-compose down -v
	docker system prune -f

backup: ## Run backup script
	./scripts/backup.sh

restore: ## Run restore script
	./scripts/restore.sh

monitor: ## Run monitoring script
	./scripts/monitor.sh

deploy: ## Deploy to production
	./deploy.sh

deploy-prod: ## Full production deployment
	./deploy-production.sh

shell-backend: ## Open shell in backend container
	docker-compose exec backend /bin/bash

shell-db: ## Open PostgreSQL shell
	docker-compose exec postgres psql -U student_admin -d admission_forms

test: ## Run tests
	docker-compose exec backend python -m pytest tests/

health: ## Check service health
	@echo "Checking service health..."
	@curl -f http://localhost:8000/health && echo "✅ Backend healthy" || echo "❌ Backend unhealthy"
	@curl -f http://localhost:3000/health && echo "✅ Frontend healthy" || echo "❌ Frontend unhealthy"
	@docker-compose exec -T postgres pg_isready -U student_admin && echo "✅ Database healthy" || echo "❌ Database unhealthy"
