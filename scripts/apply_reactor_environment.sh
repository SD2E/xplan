#!/usr/bin/env bash

OLD_DIR=`pwd`
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# source the script enviroment
. $DIR/script_environment.sh

# Check that we are actually in the right env
if [ -f ${REACTOR_BACKUP_TAG_FILE} ]; then
    echo "apply_reactor_environment applied twice."
    echo "Aborting!"
    exit 1
fi
touch ${REACTOR_BACKUP_TAG_FILE}

set -x # activate debugging 
cd ${REACTOR_DIR}

# refresh backup files
cp config.yml config.yml.back
cp reactor.rc reactor.rc.back
cp Dockerfile Dockerfile.back

# reactor.rc
sed -i "s@REACTOR_NAME=xplan2-reactor@REACTOR_NAME=${REACTOR_NAME}@g" reactor.rc
sed -i "s@REACTOR_ALIAS=xplan2@REACTOR_ALIAS=${REACTOR_ALIAS}@g" reactor.rc
sed -i "s@DOCKER_HUB_ORG=jladwigsift@DOCKER_HUB_ORG=${REACTOR_DOCKER_HUB_ORG}@g" reactor.rc
sed -i "s@DOCKER_IMAGE_TAG=xplan2@DOCKER_IMAGE_TAG=${REACTOR_DOCKER_IMAGE_TAG}@g" reactor.rc
sed -i "s@DOCKER_IMAGE_VERSION=2.0@DOCKER_IMAGE_VERSION=${REACTOR_DOCKER_IMAGE_VERSION}@g" reactor.rc

# config.yml
if [ -n "${XPLAN_EMAIL}" ]; then
    sed -i "s/email: ~/email: ${XPLAN_EMAIL}/g" config.yml
fi

## abaco won't pass along build args, so have to sed in the arg value into the Dockerfile
echo "XPLAN_DESIGN_APP_ID=${XPLAN_DESIGN_APP_ID}"
# echo "sed -i "s@XPLAN_DESIGN_APP_ID=['\"]jladwig_xplan2_design-0.0.1['\"]@XPLAN_DESIGN_APP_ID=\"${XPLAN_DESIGN_APP_ID}\"@g" Dockerfile"
sed -i "s@XPLAN_DESIGN_APP_ID=['\"]jladwig_xplan2_design-0.0.1['\"]@XPLAN_DESIGN_APP_ID=\"${XPLAN_DESIGN_APP_ID}\"@g" Dockerfile
sed -i "s@APP_DEPLOYMENT_SYSTEM=['\"]data-tacc-work-jladwig['\"]@APP_DEPLOYMENT_SYSTEM=\"${APP_DEPLOYMENT_SYSTEM}\"@g" Dockerfile

cd ${OLD_DIR}
set +x # deactivate debugging