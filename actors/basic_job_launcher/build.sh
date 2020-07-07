#!/usr/bin/env bash

CONTAINER_TAG="jladwigsift/basic-job-launcher"
VERSION=0.1

CONTAINER_FULL_NAME=${CONTAINER_TAG}:${VERSION}

echo "Building container: ${CONTAINER_FULL_NAME}"
docker build -t ${CONTAINER_FULL_NAME} .
