#!/usr/bin/env bash

REMOTE_WORKDIR=$1

if [ -z "${APP_BASE_PATH}" ]; then
    echo
    echo "ERROR:"
    echo "It appears APP_BASE_PATH has not been set in your .environment file."
    echo "Please set it to run this test."
    echo
    exit 1
fi

tapis files mkdir agave://${REMOTE_WORKDIR} ${APP_BASE_PATH}/YEAST_STATES/experiments/experiment.transcriptic.2020-05-04-YeastSTATES-1-0-Growth-Curves
tapis files upload agave://${REMOTE_WORKDIR}/${APP_BASE_PATH}/YEAST_STATES/experiments/experiment.transcriptic.2020-05-04-YeastSTATES-1-0-Growth-Curves components/xplan_design/test/resources/YEAST_STATES/experiments/experiment.transcriptic.2020-05-04-YeastSTATES-1-0-Growth-Curves/request_experiment.transcriptic.2020-05-04-YeastSTATES-1-0-Growth-Curves.json

STATE_JSON=`tapis files list agave://data-tacc-work-jladwig/xplan-reactor/YEAST_STATES/ | grep "state.json"`
if [ -z "$STATE_JSON" ]; then
    echo "No state.json found. Uploading default state."
    tapis files upload agave://${REMOTE_WORKDIR}/${APP_BASE_PATH}/YEAST_STATES/ components/xplan_design/test/defaults/state.json
fi

# tapis files mkdir agave://${REMOTE_WORKDIR}/${APP_BASE_PATH} secrets
# tapis files upload agave://${REMOTE_WORKDIR}/${APP_BASE_PATH}/secrets secrets/tx_secrets.json

OLD_DIR=`pwd`
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# source the script enviroment
. $DIR/script_environment.sh

##########################################
# Applying Design App Environment
##########################################
$DIR/apply_design_app_environment.sh

echo "==========================================="
echo "========== start design job.json =========="
echo "==========================================="
cat ${DESIGN_DIR}/job.json
echo " " # for when no newline at end of dockerfile
echo "=========================================="
echo "=========== end design job.json =========="
echo "=========================================="

echo tapis jobs submit -F ${DESIGN_DIR}/job.json
tapis jobs submit -F ${DESIGN_DIR}/job.json

$DIR/restore_design_app_environment.sh
##########################################
# Restored Design App Environment
##########################################
