#!/usr/bin/env bash

OLD_DIR=`pwd`
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# source the script enviroment
. $DIR/script_environment.sh

# Check that we are actually in the right env
if [ ! -f ${DESIGN_BACKUP_TAG_FILE} ]; then
    echo "restore_design_app_environment.sh called without apply."
    echo "Aborting!"
    exit 1
fi
rm ${DESIGN_BACKUP_TAG_FILE}

set -x # activate debugging 
cd ${DESIGN_DIR}

# Reset from back files
mv Dockerfile.back Dockerfile 
mv project.ini.back project.ini 

cd ${OLD_DIR}
set +x # deactivate debugging