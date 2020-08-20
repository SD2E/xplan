#!/bin/bash

TMP_OUT=$1
IMAGE=$2
INSTANCE=$3

mkdir -p ${TMP_OUT}


SECRETS=`pwd`/secrets
RESOURCES=`pwd`/components/xplan_design/test/resources

docker run --mount type=bind,source=${RESOURCES},target=/resources,readonly \
           --mount type=bind,source=${SECRETS},target=/${SECRETS},readonly \
           --mount type=bind,source=${TMP_OUT},target=/${TMP_OUT} \
           -t ${IMAGE} \
           resources/${INSTANCE} /${SECRETS}/tx_secrets.json /${TMP_OUT}
echo "run_docker.sh Complete"