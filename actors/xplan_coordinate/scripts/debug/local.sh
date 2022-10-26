#!/usr/bin/env bash

COMMAND=$1

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
COMMAND_DIR="${DIR}/../../test/command/"

CONTAINER_TAG="jladwigsift/xplan2"
VERSION=2.0

CONTAINER_IMAGE=${CONTAINER_TAG}:${VERSION}

# Set the Reactor.local flag. Also ensures DOCKER_ENVS is not empty
DOCKER_ENVS="-e LOCALONLY=1 ${DOCKER_ENVS}"
echo "DOCKER_ENVS: $DOCKER_ENVS"

# Agave API integration
if [ -z "${AGAVE_CREDS}" ]; then
    AGAVE_CREDS="${HOME}/.agave"
fi
# if [ ! -f "${AGAVE_CREDS}/current" ]; then
#     echo "No Agave API credentials found in ${AGAVE_CREDS}"
#     exit 1
# fi
echo "AGAVE_CREDS: $AGAVE_CREDS"

if [ -z "${TEMP}" ]; then
    TEMP=${PWD}"/tmp"
fi
echo "TEMP: $TEMP"

docker run --rm -it -v ${AGAVE_CREDS}:/root/.agave:rw \
           -v ${TEMP}:/mnt/ephemeral-01:rw \
           -v ${COMMAND_DIR}:/debug-commands:ro \
           ${DOCKER_ENVS} \
           ${MOUNTS} \
           ${CONTAINER_IMAGE} \
           /bin/bash \
           -c "cd / && cp /debug-commands/${COMMAND} /run-debug && /run-debug && /bin/bash"
