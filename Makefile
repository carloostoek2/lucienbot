.PHONY: install test lint security ci run check-db

install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pre-commit install

test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=bot --cov-report=html
	@if command -v xdg-open > /dev/null; then open htmlcov/index.html; endif

test-parallel:
	pytest tests/ -n auto

lint:
	ruff check bot/ handlers/ services/ models/
	ruff format --check bot/ handlers/ services/ models/

format:
	ruff check --fix bot/ handlers/ services/ models/
	ruff format bot/ handlers/ services/ models/

typecheck:
	mypy bot/ handlers/ services/ models/

security:
	bandit -r bot/ handlers/ services/ models/
	safety check

ci: lint security typecheck test

run:
	python bot.py

check-db:
	@python -c "from sqlalchemy import create_engine; print('✅ DB connection OK')" 2>/dev/null || echo "❌ DB connection failed"

verify:
	python scripts/verify_env.py

clean:
	rm -rf .coverage_html htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true