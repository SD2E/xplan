#!/usr/bin/env bash

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

# source the script enviroment
. $DIR/script_environment.sh

set -x # activate debugging 

##########################################
# Applying XPlan Reactor Environment
##########################################
$DIR/apply_reactor_environment.sh
cd ${REACTOR_DIR}

# print it to confirm the environment is applied
set +x # deactivate debugging
echo "=============================================="
echo "========== start Reactor Dockerfile =========="
echo "=============================================="
cat Dockerfile
echo " " # for when no newline at end of file
echo "============================================="
echo "=========== end Reactor Dockerfile =========="
echo "============================================="

echo "======================================"
echo "========== start reactor.rc =========="
echo "======================================"
cat reactor.rc
echo " " # for when no newline at end of file
echo "====================================="
echo "=========== end reactor.rc =========="
echo "====================================="

echo "======================================"
echo "========== start config.yml =========="
echo "======================================"
cat config.yml
echo " " # for when no newline at end of file
echo "====================================="
echo "=========== end config.yml =========="
echo "====================================="
set -x # activate debugging 

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

cd ${OLD_DIR}
$DIR/restore_reactor_environment.sh
##########################################
# Restored XPlan Reactor Environment
##########################################

set +x # deactivate debugging