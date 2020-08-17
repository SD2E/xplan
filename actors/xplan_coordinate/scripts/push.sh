#!/usr/bin/env bash

CONTAINER_TAG="jladwigsift/xplan-coordinate"
VERSION=0.1

CONTAINER_FULL_NAME=${CONTAINER_TAG}:${VERSION}

echo "Pushing container: ${CONTAINER_FULL_NAME}"
docker push ${CONTAINER_FULL_NAME}
