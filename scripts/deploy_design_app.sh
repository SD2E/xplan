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
cd ${OLD_DIR}

## tapis requires that docker build context is the same as the working directory
ln -s apps/xplan_design/assets/ assets
cp -r xplan-dev-env/xplan_models apps/xplan_design
cp -r components/xplan_utils apps/xplan_design
cp -r components/xplan_design apps/xplan_design
tapis app deploy -W apps/xplan_design
rm -rf apps/xplan_design/xplan_models
rm -rf apps/xplan_design/xplan_utils
rm -rf apps/xplan_design/xplan_design
rm assets
docker push ${APP_CONTAINER_FULL_NAME}

# Reset from back files
mv ${DESIGN_DIR}/Dockerfile.back ${DESIGN_DIR}/Dockerfile 
mv ${DESIGN_DIR}/project.ini.back ${DESIGN_DIR}/project.ini 

set +x # deactivate debugging