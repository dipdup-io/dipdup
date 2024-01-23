.PHONY: $(MAKECMDGOALS)
MAKEFLAGS += --no-print-directory
##
##  🚧 DipDup developer tools
##
PACKAGE=dipdup
TAG=latest
SOURCE=src tests scripts
DEMO=''
FRONTEND_PATH=../interface


help:           ## Show this help (default)
	@grep -Fh "##" $(MAKEFILE_LIST) | grep -Fv grep -F | sed -e 's/\\$$//' | sed -e 's/##//'

all:            ## Run an entire CI pipeline
	make format lint test

format:         ## Format with all tools
	make black

lint:           ## Lint with all tools
	make ruff mypy

test:           ## Run tests
	pytest --cov-report=term-missing --cov=dipdup --cov-report=xml -n auto -s -v tests

##

black:          ## Format with black
	black ${SOURCE}

ruff:           ## Lint with ruff
	ruff check --fix ${SOURCE}

mypy:           ## Lint with mypy
	mypy --no-incremental --exclude ${PACKAGE} ${SOURCE}

##

image:          ## Build Docker image
	docker buildx build . -t ${PACKAGE}:${TAG}

##

demos:          ## Recreate demo projects from templates
	python scripts/demos.py render ${DEMO}
	python scripts/demos.py init ${DEMO}
	pdm run format
	pdm run lint

docs_build:     ## Build docs
	python scripts/docs.py check-links --source docs
	python scripts/docs.py markdownlint
	python scripts/docs.py dump-references
	python scripts/docs.py dump-jsonschema
	python scripts/docs.py build --source docs --destination ${FRONTEND_PATH}/content/docs

docs_serve:     ## Build docs and start frontend server
	python scripts/docs.py build --source docs --destination ${FRONTEND_PATH}/content/docs --watch --serve

docs_watch:     ## Build docs and watch for changes
	python scripts/docs.py build --source docs --destination ${FRONTEND_PATH}/content/docs --watch

fixme:          ## Find FIXME and TODO comments
	grep -r -e 'FIXME: ' -e 'TODO: ' -e 'type: ignore' -n src/dipdup --color

update:         ## Update dependencies and dump requirements.txt
	pdm update
	pdm export --without-hashes -f requirements --prod -o requirements.txt
	pdm export --without-hashes -f requirements --dev -o requirements.dev.txt

before_release: ## Prepare for a new release after updating version in pyproject.toml
	make format
	make lint
	make update
	make demos
	make test
	make docs_build
	echo "🎉 Commit changes, merge `aux/X.Y.Z`, run 'git checkout next && git pull && git tag X.Y.Z && git push origin X.Y.Z'" 
##