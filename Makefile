.PHONY: help install run test lint autofmt clean migrate makemigrations shell collectstatic

# Default target
help:
	@echo "Available commands:"
	@echo "  install        - Install dependencies in virtual environment"
	@echo "  run           - Start development server"
	@echo "  test          - Run tests"
	@echo "  lint          - Run code quality checks"
	@echo "  autofmt       - Auto-format code"
	@echo "  clean         - Clean up cache and temporary files"
	@echo "  migrate       - Apply database migrations"
	@echo "  makemigrations - Create new migrations"
	@echo "  shell         - Open Django shell"
	@echo "  collectstatic - Collect static files"

# Installation and setup
install:
	@if [ ! -d "venv" ]; then \
		python3 -m venv venv; \
	fi
	. venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt

# Development server
run:
	@echo "Starting development server..."
	python manage.py runserver

# Database operations
makemigrations:
	@echo "Creating migrations..."
	python manage.py makemigrations

migrate:
	@echo "Applying migrations..."
	python manage.py migrate

# Code quality
isort:
	@echo "Sorting imports..."
	isort .

isortcheck:
	@echo "Checking import sorting..."
	isort --diff --check-only .

black:
	@echo "Formatting code with black..."
	black .

blackcheck:
	@echo "Checking code formatting..."
	black --check .

pyformatcheck: isortcheck blackcheck

mypy:
	@echo "Running type checking..."
	mypy .

lint: pyformatcheck mypy

autofmt: isort black

# Testing
test:
	@echo "Running tests..."
	python manage.py test

# Django utilities
shell:
	@echo "Opening Django shell..."
	python manage.py shell

collectstatic:
	@echo "Collecting static files..."
	python manage.py collectstatic --noinput

# Cleanup
clean:
	@echo "Cleaning up..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf .mypy_cache

# Pre-commit hooks
precommit: autofmt lint test

# Production preparation
production: clean collectstatic migrate

# Database operations
setupdb: makemigrations migrate

# Quick development setup
dev: install setupdb run