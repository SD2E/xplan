#!/usr/bin/env bash

tapis files mkdir agave://${REMOTE_WORK_DIR} ${REACTOR_BASE_PATH}/${CHALLENGE_PROBLEM}/experiments/${EXPERIMENT_ID}
tapis files upload agave://${REMOTE_WORK_DIR}/${REACTOR_BASE_PATH}/${CHALLENGE_PROBLEM}/experiments/${EXPERIMENT_ID} components/xplan_design/test/resources/${CHALLENGE_PROBLEM}/experiments/${EXPERIMENT_ID}/request_${EXPERIMENT_ID}.json

#tapis files mkdir agave://${REMOTE_WORK_DIR}/${REACTOR_BASE_PATH} secrets
#tapis files upload agave://${REMOTE_WORK_DIR}/${REACTOR_BASE_PATH}/secrets secrets/tx_secrets.json

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
ACTOR_ID=`tapis actors list | grep ${REACTOR_NAME} | cut -f 2 -d "|"`

MSG_FILE=$DIR/../actors/xplan_coordinate/test/file/gen-experiment-request-message-factors.json.sample
MSG=`sed "s@data-tacc-work-jladwig@${REMOTE_WORK_DIR}@g;s@xplan2@${REACTOR_BASE_PATH}@g;s@experiment.transcriptic.2020-05-04-YeastSTATES-1-0-Growth-Curves@${EXPERIMENT_ID}@g;s@YEAST_STATES@${CHALLENGE_PROBLEM}@g;s@invocation@request@g" ${MSG_FILE}`
echo ${MSG}
tapis actors submit -m "${MSG}" ${ACTOR_ID}
