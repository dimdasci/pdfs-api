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

configure-ecr-policy:
	aws ecr put-lifecycle-policy \
		--repository-name pdfaapiprod41beddd1/apihandlerfunctionb1de9107repo \
		--lifecycle-policy-text file://ecr-lifetime-policy.json \
		--profile dimds \
		--output yaml

configure-s3-notifications-prod:
	$(eval STACK_NAME := pdfa-api-prod) # Adjust if your prod stack name is different
	$(eval PDF_BUCKET_NAME := dimosaic-pdf-analyser-svhy308sv6) # From your template Globals
	$(eval AWS_REGION := eu-central-1) # Inferred from your template (e.g., JwtAuthorizer ARN)
	$(eval AWS_PROFILE := dimds) # As used in other Makefile targets
	@echo "Fetching SQS Queue ARN from stack $(STACK_NAME)..."
	$(eval SQS_QUEUE_ARN := $(shell aws cloudformation describe-stacks --stack-name $(STACK_NAME) --query "Stacks[0].Outputs[?OutputKey=='PdfProcessingSqsQueueArn'].OutputValue" --output text --profile $(AWS_PROFILE) --region $(AWS_REGION)))
	@if [ -z "$(SQS_QUEUE_ARN)" ]; then \
		echo "Error: Could not retrieve SQS Queue ARN. Ensure the stack is deployed and the output 'PdfProcessingSqsQueueArn' exists."; \
		exit 1; \
	fi
	@echo "Configuring S3 bucket $(PDF_BUCKET_NAME) to send notifications to SQS queue $(SQS_QUEUE_ARN)..."
	aws s3api put-bucket-notification-configuration \
		--bucket $(PDF_BUCKET_NAME) \
		--notification-configuration '{"QueueConfigurations": [{"Id": "S3ToSqsPdfProcessingEvents", "QueueArn": "$(SQS_QUEUE_ARN)", "Events": ["s3:ObjectCreated:Put"], "Filter": {"Key": {"FilterRules": [{"Name": "suffix", "Value": ".pdf"}]}}}]}' \
		--profile $(AWS_PROFILE) \
		--region $(AWS_REGION)
	@echo "S3 notification configuration updated successfully for bucket $(PDF_BUCKET_NAME) (PDF files only)."

.PHONY: install install-dev tests format build deploy-prod deploy-prod-guided configure-ecr-policy