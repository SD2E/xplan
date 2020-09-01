#!/usr/bin/env bash

XPLAN_DESIGN_APP_ID="${APP_NAME}-${APP_VERSION}"

ACTOR_ID=`tapis actors list | grep ${REACTOR_NAME} | cut -f 2 -d "|"`

if [ -z ${ACTOR_ID} ]; then

  CONTAINER_FULL_NAME=${REACTOR_DOCKER_HUB_ORG}/${REACTOR_DOCKER_IMAGE_TAG}:${REACTOR_DOCKER_IMAGE_VERSION}
  echo "tapis actors create --repo ${CONTAINER_FULL_NAME} \
                      --stateful \
                      -n ${REACTOR_NAME}"
  tapis actors create --repo ${CONTAINER_FULL_NAME} \
                      --stateful \
                      -n ${REACTOR_NAME}
  ACTOR_ID=`tapis actors list | grep ${REACTOR_NAME} | cut -f 2 -d "|"`

fi

OLD_DIR=`pwd`
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

set -x # activate debugging 

REACTOR_DIR="${DIR}/../actors/xplan_coordinate"

# refresh backup files
cp ${REACTOR_DIR}/config.yml ${REACTOR_DIR}/config.yml.back
cp ${REACTOR_DIR}/reactor.rc ${REACTOR_DIR}/reactor.rc.back

cd ${REACTOR_DIR}
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
echo $XPLAN_DESIGN_APP_ID
# echo "sed -i "s@XPLAN_DESIGN_APP_ID=['\"]jladwig_xplan_design-0.0.1['\"]@XPLAN_DESIGN_APP_ID=\"${XPLAN_DESIGN_APP_ID}\"@g" Dockerfile"
sed -i "s@XPLAN_DESIGN_APP_ID=['\"]jladwig_xplan_design-0.0.1['\"]@XPLAN_DESIGN_APP_ID=\"${XPLAN_DESIGN_APP_ID}\"@g" Dockerfile
sed -i "s@APP_DEPLOYMENT_SYSTEM=['\"]data-tacc-work-jladwig['\"]@APP_DEPLOYMENT_SYSTEM=\"${APP_DEPLOYMENT_SYSTEM}\"@g" Dockerfile

cat Dockerfile
cp -r $DIR/../xplan-dev-env/xplan_models ./xplan_models
cp -r $DIR/../components/xplan_utils ./xplan_utils
cp -r $DIR/../components/xplan_design ./xplan_design
cp -r $DIR/../components/xplan_submit ./xplan_submit

docker build -f ${REACTOR_DIR}/Dockerfile -t ${REACTOR_CONTAINER_FULL_NAME} ${REACTOR_DIR}
docker push ${REACTOR_CONTAINER_FULL_NAME}
# use -f tp force an update even if the image tag is identical
abaco update -f ${ACTOR_ID} ${REACTOR_CONTAINER_FULL_NAME}

rm -rf ./xplan_models
rm -rf ./xplan_utils
rm -rf ./xplan_design
rm -rf ./xplan_submit

# Reset from back files
mv ${REACTOR_DIR}/config.yml.back ${REACTOR_DIR}/config.yml
mv ${REACTOR_DIR}/reactor.rc.back ${REACTOR_DIR}/reactor.rc

set +x # deactivate debugging

# return to original directory
cd ${OLD_DIR}