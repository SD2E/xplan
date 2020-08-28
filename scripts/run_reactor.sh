#!/usr/bin/env bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
ACTOR_ID=`tapis actors list | grep ${REACTOR_NAME} | cut -f 2 -d "|"`

MSG_FILE=$DIR/../actors/xplan_coordinate/test/file/xplan-design-message-invocation.json.sample
MSG=`sed "s@data-tacc-work-jladwig@${REMOTE_WORK_DIR}@g" ${MSG_FILE}`
echo ${MSG}
tapis actors submit -m "${MSG}" ${ACTOR_ID}
