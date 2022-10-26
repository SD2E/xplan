#!/usr/bin/env bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# source the script enviroment
. $DIR/script_environment.sh

set -x # activate debugging 

##########################################
# Applying Design App Environment
##########################################
$DIR/apply_design_app_environment.sh

# print it to confirm the environment is applied
set +x # deactivate debugging
echo "================================================="
echo "========== start Design App Dockerfile =========="
echo "================================================="
cat ${DESIGN_DIR}/Dockerfile
echo " " # for when no newline at end of dockerfile
echo "================================================"
echo "=========== end Design App Dockerfile =========="
echo "================================================"
set -x # activate debugging 

cp -r $DIR/../components/xplan_design ${DESIGN_DIR}
cp -r $DIR/../components/xplan_models ${DESIGN_DIR}
cp -r $DIR/../components/xplan_utils ${DESIGN_DIR}
docker build -f ${DESIGN_DIR}/Dockerfile -t ${APP_CONTAINER_FULL_NAME} ${DESIGN_DIR}
rm -rf ${DESIGN_DIR}/xplan_design
rm -rf ${DESIGN_DIR}/xplan_models
rm -rf ${DESIGN_DIR}/xplan_utils

$DIR/restore_design_app_environment.sh
##########################################
# Restored Design App Environment
##########################################

set +x # deactivate debugging