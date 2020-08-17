#!/usr/bin/env bash

CONTAINER_TAG="jladwigsift/xplan-coordinate"
VERSION=0.1

CONTAINER_IMAGE=${CONTAINER_TAG}:${VERSION}

# Load up the message to send
if [ ! -z "$1" ]; then
  MESSAGE_PATH=$1
  shift
fi
MESSAGE=
if [ -f "${MESSAGE_PATH}" ]; then
    echo "Reading message from ${MESSAGE_PATH}"
    MESSAGE=$(cat ${MESSAGE_PATH})
fi
if [ -z "${MESSAGE}" ]; then
    echo "Message not readable from ${MESSAGE_PATH}"
    exit 1
fi
echo "MESSAGE:"
echo "$MESSAGE"

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
           -e MSG="${MESSAGE}" \
           ${DOCKER_ENVS} \
           ${MOUNTS} \
           ${CONTAINER_IMAGE}
