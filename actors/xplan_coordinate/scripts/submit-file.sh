#!/usr/bin/env bash

MESSAGE=$1
ACTOR_ID=$2
tapis actors submit -F ${MESSAGE} ${ACTOR_ID}

