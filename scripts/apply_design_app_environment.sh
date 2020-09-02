#!/usr/bin/env bash

OLD_DIR=`pwd`
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# source the script enviroment
. $DIR/script_environment.sh

# Check that we are actually in the right env
if [ -f ${DESIGN_BACKUP_TAG_FILE} ]; then
    echo "apply_design_app_environment.sh applied twice."
    echo "Aborting!"
    exit 1
fi
touch ${DESIGN_BACKUP_TAG_FILE}

set -x # activate debugging 
cd ${DESIGN_DIR}

cp Dockerfile Dockerfile.back
cp project.ini project.ini.back

# app
sed -i "s@name = jladwig_xplan2_design@name = ${APP_NAME}@g" project.ini
sed -i "s@deployment_system = data-tacc-work-jladwig@deployment_system = ${APP_DEPLOYMENT_SYSTEM}@g" project.ini
sed -i "s@execution_system = hpc-tacc-wrangler-jladwig@execution_system = ${APP_EXECUTION_SYSTEM}@g" project.ini
sed -i "s@version = 0.0.1@version = ${APP_VERSION}@g" project.ini
# docker
sed -i "s@namespace = jladwigsift@namespace = ${APP_DOCKER_NAMESPACE}@g" project.ini
sed -i "s@repo = xplan_design@repo = ${APP_DOCKER_REPO}@g" project.ini
sed -i "s@tag = 0.0.1@tag = ${APP_DOCKER_TAG}@g" project.ini

cd ${OLD_DIR}
set +x # deactivate debugging