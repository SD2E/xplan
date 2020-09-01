#!/usr/bin/env bash

OLD_DIR=`pwd`
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

set -x # activate debugging 

DESIGN_DIR="${DIR}/../apps/xplan_design"

$DIR/build_design.app.sh
docker push ${APP_CONTAINER_FULL_NAME}

## tapis requires that docker build context is the same as the working directory
ln -s apps/xplan_design/assets/ assets
tapis app deploy --no-build --no-push -W ${DESIGN_DIR}
rm assets

set +x # deactivate debugging