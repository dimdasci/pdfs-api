install:
	pip install -r requirements.txt

install-dev: install
	pip install -r requirements-dev.txt

tests:
	python -m unittest discover tests 

format:
	isort src tests
	ruff format src tests

build:
	sam validate --lint
	docker image prune -f
	sam build --use-container --no-cached

deploy-prod:
	sam deploy \
		--config-file samconfig.toml \
		--config-env prod \
		--no-fail-on-empty-changeset \
		--parameter-overrides \
			ParameterKey=ReleaseVersion,ParameterValue=$(shell git describe --tags --tags --abbrev=0) \
			ParameterKey=ReleaseCommitHash,ParameterValue=$(shell git rev-parse HEAD) \
			ParameterKey=StageName,ParameterValue=prod \
			ParameterKey=CorsAllowedOrigin,ParameterValue=https://dimosaic.dev

deploy-prod-guided:
	sam deploy \
		--guided \
		--config-file samconfig.toml \
		--config-env prod \
		--no-fail-on-empty-changeset \
		--parameter-overrides \
			ParameterKey=ReleaseVersion,ParameterValue=$(shell git describe --tags --tags --abbrev=0) \
			ParameterKey=ReleaseCommitHash,ParameterValue=$(shell git rev-parse HEAD) \
			ParameterKey=StageName,ParameterValue=prod \
			ParameterKey=CorsAllowedOrigin,ParameterValue=https://dimosaic.dev \
		--profile dimds
