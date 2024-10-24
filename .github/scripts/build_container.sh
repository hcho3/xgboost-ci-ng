#!/bin/bash
## Build a CI container and cache the layers in an S3 bucket.
## Build-time variables (--build-arg) and container defintion are fetched from
## ops/matrix/ci_container.yml.
##
## Note. This script takes in all inputs via environment variables.
##
## Inputs
## - CONTAINER_ID: String ID uniquely identifying the built container.
## - GITHUB_REPOSITORY: Current GitHub repository (e.g. dmlc/xgboost)
## - S3_BUCKET: Name of the S3 bucket
## - S3_REGION: Region the S3 bucket is located at (e.g. us-west-2)

set -euo pipefail

# Fetch CONTAINER_DEF and BUILD_ARGS
source <(ops/matrix/extract_build_args.sh ${CONTAINER_ID} | tee /dev/stderr) 2>&1

# Run Docker build
set -x
python3 ops/docker_build.py \
  --container-def ${CONTAINER_DEF} \
  --container-id ${CONTAINER_ID} \
  ${BUILD_ARGS} \
  --cache-from type=s3,blobs_prefix=cache/${GITHUB_REPOSITORY}/,manifests_prefix=cache/${GITHUB_REPOSITORY}/,region=${S3_REGION},bucket=${S3_BUCKET} \
  --cache-to type=s3,blobs_prefix=cache/${GITHUB_REPOSITORY}/,manifests_prefix=cache/${GITHUB_REPOSITORY}/,region=${S3_REGION},bucket=${S3_BUCKET},mode=max
set +x
