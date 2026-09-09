.PHONY: help spike up down logs test lint fmt

help:
	@echo "spike  - run the S0 design spike CLI"
	@echo "up     - start the local stack"
	@echo "down   - stop the local stack"
	@echo "logs   - tail backend logs"
	@echo "test   - run backend tests"
	@echo "lint   - ruff + mypy"
	@echo "fmt    - format backend and frontend"

spike:
	cd backend && python ../scripts/spike.py --suite

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f coffee-backend

test:
	cd backend && pytest -v

lint:
	cd backend && ruff check . && mypy app

fmt:
	cd backend && ruff format .
	cd frontend && npm run format
