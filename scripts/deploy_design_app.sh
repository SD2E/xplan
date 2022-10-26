#!/usr/bin/env bash

OLD_DIR=`pwd`
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# source the script enviroment
. $DIR/script_environment.sh

set -x # activate debugging 

# Do these *before* calling the backup_design_app_files script
# because build_design_app also does backups
$DIR/build_design_app.sh

# push the built image. This should have no need for sed changes
docker push ${APP_CONTAINER_FULL_NAME}

##########################################
# Applying Design App Environment
##########################################
$DIR/apply_design_app_environment.sh

## tapis requires that docker build context is the same as the working directory
ln -s apps/xplan_design/assets/ assets

# print it to confirm the environment is applied
set +x # deactivate debugging
echo "======================================="
echo "========== start project.ini =========="
echo "======================================="
cat ${DESIGN_DIR}/project.ini
echo "======================================="
echo "=========== end project.ini ==========="
echo "======================================="
echo "======================================="
echo "========== start app.json =========="
echo "======================================="
cat ${DESIGN_DIR}/app.json
echo "======================================="
echo "=========== end app.json ==========="
echo "======================================="
set -x # activate debugging

tapis app deploy --no-build --no-push -W ${DESIGN_DIR}
rm assets

$DIR/restore_design_app_environment.sh
##########################################
# Restored Design App Environment
##########################################

set +x # deactivate debugging