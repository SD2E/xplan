#!/bin/bash

TMP_OUT=$1
IMAGE=$2
INSTANCE=$3

mkdir -p ${TMP_OUT}


SECRETS=`pwd`/secrets
RESOURCES=`pwd`/components/xplan_design/test/resources

docker run -v ${RESOURCES}:/resources -v ${SECRETS}:/${SECRETS} -v ${TMP_OUT}:/${TMP_OUT} \
           -t ${IMAGE} \
           resources/${INSTANCE} /${SECRETS}/tx_secrets.json ${TMP_OUT}
echo "run_docker.sh Complete"