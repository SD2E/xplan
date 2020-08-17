#!/usr/bin/env bash

CONTAINER_TAG="jladwigsift/xplan-coordinate"
VERSION=0.1

CONTAINER_FULL_NAME=${CONTAINER_TAG}:${VERSION}

tapis actors create --repo $CONTAINER_FULL_NAME \
                      --stateful \
                      -n dev-xplan-coordinate \
                      -d "coordinate"