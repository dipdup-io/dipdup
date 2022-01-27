all: install lint test cover
lint: isort black flake mypy

install:
	poetry install

isort:
	poetry run isort src

black:
	poetry run black src

flake:
	poetry run flakehell lint src

mypy:
	poetry run mypy src

test:
	poetry run pytest --cov-report=term-missing --cov={{ cookiecutter.package }} --cov-report=xml -v tests

cover:
	poetry run diff-cover coverage.xml

build:
	poetry build

image:
	docker build . -t {{ cookiecutter.project_name }}:latest

up:
	docker-compose up -d

down:
	docker-compose down
