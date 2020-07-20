#!/usr/bin/env bash

CONTAINER_TAG="jladwigsift/xplan-coordinate"
VERSION=0.1

CONTAINER_FULL_NAME=${CONTAINER_TAG}:${VERSION}

echo "Building container: ${CONTAINER_FULL_NAME}"
cp -r ../../../xplan_models ./xplan_models
cp -r ../../components/xplan_utils ./xplan_utils
cp -r ../../components/xplan_design ./xplan_design
docker build -t ${CONTAINER_FULL_NAME} .
rm -rf ./xplan_models
rm -rf ./xplan_utils
rm -rf ./xplan_design
