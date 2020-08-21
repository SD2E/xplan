#!/usr/bin/env bash

ACTOR_ID=$1
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
tapis actors submit -F $DIR/../test/file/xplan-design-message.json.sample ${ACTOR_ID}

