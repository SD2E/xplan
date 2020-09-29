#!/bin/bash

TMP_OUT=$1
IMAGE=$2
EXPERIMENT_ID=$3
CHALLENGE_PROBLEM=$4

mkdir -p ${TMP_OUT}

SECRETS=`pwd`/secrets
RESOURCES=`pwd`/components/xplan_design/test/resources
cp -R ${RESOURCES}/${CHALLENGE_PROBLEM} ${TMP_OUT} # Inputs are same location as outputs


docker run --mount type=bind,source=${SECRETS},target=/${SECRETS},readonly \
           --mount type=bind,source=${TMP_OUT},target=/${TMP_OUT} \
           -t ${IMAGE} \
           ${EXPERIMENT_ID} ${CHALLENGE_PROBLEM} /${SECRETS}/tx_secrets.json /${TMP_OUT} /${TMP_OUT} /${TMP_OUT}/state.json
echo "run_docker.sh Complete"