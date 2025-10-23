.PHONY: install-dev lint typecheck fix up build down logs

install-dev:
	. .venv/bin/activate && pip install -U pip && pip install -r requirements.txt && pip install -r dev-requirements.txt

ruff-check:
	ruff check .

ruff-fix:
	ruff check . --fix 

ruff-format:
	ruff format .

mypy:
	mypy .

up:
	docker compose --env-file .env up --build

build:
	docker compose --env-file .env build

run:
	docker compose --env-file .env run

down:
	docker compose down

logs:
	docker compose logs -f
