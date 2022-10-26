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
cp job.json job.json.back

# app
sed -i "s@name = jladwig_xplan2_design@name = ${APP_NAME}@g" project.ini
sed -i "s@deployment_system = data-tacc-work-jladwig@deployment_system = ${APP_DEPLOYMENT_SYSTEM}@g" project.ini
sed -i "s@execution_system = hpc-tacc-wrangler-jladwig@execution_system = ${APP_EXECUTION_SYSTEM}@g" project.ini
sed -i "s@version = 0.0.1@version = ${APP_VERSION}@g" project.ini
# docker
sed -i "s@namespace = jladwigsift@namespace = ${APP_DOCKER_NAMESPACE}@g" project.ini
sed -i "s@repo = xplan_design@repo = ${APP_DOCKER_REPO}@g" project.ini
sed -i "s@tag = 0.0.1@tag = ${APP_DOCKER_TAG}@g" project.ini

if [ -z "${APP_BASE_PATH}" ]; then
    echo "WARNING: Skipping some sed changes to job.json because APP_BASE_PATH is not set in the .environment"
else
    # these changes are currently only used by the 'run_tapis_app' script. That
    # script will throw an error if the variable is not set so this is just extra
    # handling in case I overlooked a use of the job.json
    sed -i "s@data-tacc-work-jladwig/xplan2@${APP_DEPLOYMENT_SYSTEM}/${APP_BASE_PATH}@g" job.json
    sed -i "s@\"out_path\": \"xplan2\"@\"out_path\": \"${APP_BASE_PATH}\"@g" job.json
fi

sed -i "s@['\"]jladwig_xplan2_design-0.0.1['\"]@${XPLAN_DESIGN_APP_ID}@g" job.json

if [ -n "${XPLAN_EMAIL}" ]; then
    sed -i "s/\"url\": null/\"url\": \"${XPLAN_EMAIL}\"/g" job.json
fi

cd ${OLD_DIR}
set +x # deactivate debugging