.ONESHELL:
.PHONY: $(MAKECMDGOALS)
MAKEFLAGS += --no-print-directory
##
##  🚧 DipDup developer tools
##
PROJECT=demo-auction
SRC=.
TAG=latest
COMPOSE=deploy/compose.yaml

help:           ## Show this help (default)
	@grep -Fh "##" $(MAKEFILE_LIST) | grep -Fv grep -F | sed -e 's/\\$$//' | sed -e 's/##//'

all:            ## Run a whole CI pipeline: formatters, linters and tests
	make format lint

format:         ## Format with all tools
	make black

lint:           ## Lint with all tools
	make ruff mypy

##

black:          ## Format with black
	black ${SRC}

ruff:           ## Lint with ruff
	ruff check ${SRC}

mypy:           ## Lint with mypy
	mypy ${SRC}

##

image:          ## Build Docker image
	docker buildx build . -t ${PROJECT}:${TAG}

up:             ## Run Compose stack
	docker-compose -f ${COMPOSE} up -d --build
	docker-compose -f ${COMPOSE} logs -f

down:           ## Stop Compose stack
	docker-compose -f ${COMPOSE} down

##