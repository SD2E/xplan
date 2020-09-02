#!/usr/bin/env bash

OLD_DIR=`pwd`
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# source the script enviroment
. $DIR/script_environment.sh

# Check that we are actually in the right env
if [ ! -f ${REACTOR_BACKUP_TAG_FILE} ]; then
    echo "restore_reactor_environment called without apply."
    echo "Aborting!"
    exit 1
fi
rm ${REACTOR_BACKUP_TAG_FILE}

set -x # activate debugging 
cd ${REACTOR_DIR}

# Reset from back files
mv config.yml.back config.yml
mv reactor.rc.back reactor.rc
mv Dockerfile.back Dockerfile

cd ${OLD_DIR}
set +x # deactivate debugging