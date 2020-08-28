#!/usr/bin/env bash

OLD_DIR=`pwd`
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

set -x # activate debugging 

DESIGN_DIR="${DIR}/../apps/xplan_design"

# refresh backup files
cp ${DESIGN_DIR}/Dockerfile ${DESIGN_DIR}/Dockerfile.back
cp ${DESIGN_DIR}/project.ini ${DESIGN_DIR}/project.ini.back

cd ${DESIGN_DIR}
# app
sed -i "s@name = jladwig_xplan_design@name = ${APP_NAME}@g" project.ini
sed -i "s@deployment_system = data-tacc-work-jladwig@deployment_system = ${APP_DEPLOYMENT_SYSTEM}@g" project.ini
sed -i "s@execution_system =  hpc-tacc-wrangler-jladwig@execution_system = ${APP_EXECUTION_SYSTEM}@g" project.ini
sed -i "s@version = 0.0.1@version = ${APP_VERSION}@g" project.ini
# docker
sed -i "s@namespace = jladwigsift@namespace = ${APP_DOCKER_NAMESPACE}@g" project.ini
sed -i "s@repo = xplan_design@repo = ${APP_DOCKER_REPO}@g" project.ini
sed -i "s@tag = 0.0.1@tag = ${APP_DOCKER_TAG}@g" project.ini

cp -r $DIR/../components/xplan_design ${DESIGN_DIR}
cp -r $DIR/../xplan-dev-env/xplan_models ${DESIGN_DIR}
cp -r $DIR/../components/xplan_utils ${DESIGN_DIR}
docker build -f ${DESIGN_DIR}/Dockerfile -t ${APP_CONTAINER_FULL_NAME} ${DESIGN_DIR}
rm -rf ${DESIGN_DIR}/xplan_design
rm -rf ${DESIGN_DIR}/xplan_models
rm -rf ${DESIGN_DIR}/xplan_utils

# Reset from back files
mv ${DESIGN_DIR}/Dockerfile.back ${DESIGN_DIR}/Dockerfile 
mv ${DESIGN_DIR}/project.ini.back ${DESIGN_DIR}/project.ini 

set +x # deactivate debugging

cd ${OLD_DIR}