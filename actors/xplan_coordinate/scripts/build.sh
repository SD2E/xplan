#!/usr/bin/env bash

CONTAINER_TAG="jladwigsift/xplan-coordinate"
VERSION=0.1

CONTAINER_FULL_NAME=${CONTAINER_TAG}:${VERSION}

echo "Building container: ${CONTAINER_FULL_NAME}"
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cp -r $DIR/../../../xplan-dev-env/xplan_models ./xplan_models
cp -r $DIR/../../../components/xplan_utils ./xplan_utils
cp -r $DIR/../../../components/xplan_design ./xplan_design
cp -r $DIR/../../../components/xplan_submit ./xplan_submit
docker build -t ${CONTAINER_FULL_NAME} .
rm -rf ./xplan_models
rm -rf ./xplan_utils
rm -rf ./xplan_design
rm -rf ./xplan_submit
