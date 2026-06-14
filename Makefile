STACK_NAME ?= nhid-clinical-api
REGION     ?= us-east-1
PROFILE    ?=

AWS_ARGS := --region $(REGION)
ifdef PROFILE
  AWS_ARGS += --profile $(PROFILE)
endif

.PHONY: build deploy destroy get-key get-url test-api logs help

help:
	@echo "Targets:"
	@echo "  build       sam build (creates .aws-sam/)"
	@echo "  deploy      build + sam deploy (first run prompts for guided setup)"
	@echo "  get-key     print the live API key value"
	@echo "  get-url     print the conformance endpoint URL"
	@echo "  test-api    curl the live endpoint with tests/sample_request.json"
	@echo "  logs        tail Lambda CloudWatch logs"
	@echo "  destroy     delete the CloudFormation stack"
	@echo ""
	@echo "Overrides:  STACK_NAME, REGION, PROFILE"

build:
	sam build $(AWS_ARGS)

deploy: build
	sam deploy \
		--stack-name $(STACK_NAME) \
		--capabilities CAPABILITY_IAM \
		--resolve-s3 \
		$(AWS_ARGS)

get-key:
	@KEY_ID=$$(aws cloudformation describe-stacks \
		--stack-name $(STACK_NAME) \
		--query "Stacks[0].Outputs[?OutputKey=='ApiKeyId'].OutputValue" \
		--output text \
		$(AWS_ARGS)); \
	aws apigateway get-api-key \
		--api-key "$$KEY_ID" \
		--include-value \
		--query "value" \
		--output text \
		$(AWS_ARGS)

get-url:
	@aws cloudformation describe-stacks \
		--stack-name $(STACK_NAME) \
		--query "Stacks[0].Outputs[?OutputKey=='ConformanceEndpoint'].OutputValue" \
		--output text \
		$(AWS_ARGS)

test-api:
	@ENDPOINT=$$($(MAKE) -s get-url); \
	KEY=$$($(MAKE) -s get-key); \
	echo "→ POST $$ENDPOINT"; \
	curl -s -X POST "$$ENDPOINT" \
		-H "x-api-key: $$KEY" \
		-H "Content-Type: application/json" \
		-d @tests/sample_request.json | python3 -m json.tool

logs:
	aws logs tail /aws/lambda/nhid-conformance-check --follow $(AWS_ARGS)

destroy:
	sam delete --stack-name $(STACK_NAME) --no-prompts $(AWS_ARGS)
