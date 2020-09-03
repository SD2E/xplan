#!/usr/bin/env bash

tapis files mkdir agave://${REMOTE_WORKDIR} xplan2/YEAST_STATES/experiments/experiment.transcriptic.2020-05-04-YeastSTATES-1-0-Growth-Curves
tapis files upload agave://${REMOTE_WORKDIR}/xplan2/YEAST_STATES/experiments/experiment.transcriptic.2020-05-04-YeastSTATES-1-0-Growth-Curves components/xplan_design/test/resources/YEAST_STATES/experiments/experiment.transcriptic.2020-05-04-YeastSTATES-1-0-Growth-Curves/request_experiment.transcriptic.2020-05-04-YeastSTATES-1-0-Growth-Curves.json

tapis files mkdir agave://${REMOTE_WORKDIR}/xplan2 secrets
tapis files upload agave://${REMOTE_WORKDIR}/xplan2/secrets secrets/tx_secrets.json

#tapis files mkdir agave://${REMOTE_WORKDIR}/xplan2 out


DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
ACTOR_ID=`tapis actors list | grep ${REACTOR_NAME} | cut -f 2 -d "|"`

MSG_FILE=$DIR/../actors/xplan_coordinate/test/file/xplan-design-message-invocation.json.sample
MSG=`sed "s@data-tacc-work-jladwig@${REMOTE_WORK_DIR}@g" ${MSG_FILE}`
echo ${MSG}
tapis actors submit -m "${MSG}" ${ACTOR_ID}
