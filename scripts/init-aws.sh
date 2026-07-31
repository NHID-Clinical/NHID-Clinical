#!/bin/bash
# LocalStack initialization script for NHID-Clinical development environment
# Creates necessary S3 buckets and IAM policies for local testing

set -e

echo "Initializing LocalStack for NHID-Clinical..."

# Wait for LocalStack to be ready
echo "Waiting for LocalStack endpoint..."
while ! curl -s http://localhost:4566 > /dev/null 2>&1; do
  echo "LocalStack not ready yet... waiting"
  sleep 2
done

echo "LocalStack is ready"

# Set AWS CLI to use LocalStack
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1

# Create S3 bucket for audit artifacts (optional, if needed for future phases)
echo "Creating S3 bucket: nhid-audit-artifacts"
aws --endpoint-url=http://localhost:4566 s3 mb s3://nhid-audit-artifacts || echo "Bucket already exists"

# Enable versioning on audit bucket (for immutability)
echo "Enabling versioning on audit bucket"
aws --endpoint-url=http://localhost:4566 s3api put-bucket-versioning \
  --bucket nhid-audit-artifacts \
  --versioning-configuration Status=Enabled || echo "Versioning already enabled"

# Create CloudWatch log group for audit logs
echo "Creating CloudWatch log group: /nhid-clinical/audit"
aws --endpoint-url=http://localhost:4566 logs create-log-group \
  --log-group-name /nhid-clinical/audit || echo "Log group already exists"

echo "LocalStack initialization complete"
