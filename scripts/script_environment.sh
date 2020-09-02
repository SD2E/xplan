#!/usr/bin/env bash

SCRIPT_ENVIRONMENT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# these can probably be embedded into the Makefile
# but perhaps they will have use outside of make
export DESIGN_DIR="${SCRIPT_ENVIRONMENT_DIR}/../apps/xplan_design"
# echo "Exporting DESIGN_DIR=${DESIGN_DIR}"
export REACTOR_DIR="${SCRIPT_ENVIRONMENT_DIR}/../actors/xplan_coordinate"
# echo "Exporting REACTOR_DIR=${REACTOR_DIR}"

# internal scripting tags to help with error messaging
export DESIGN_BACKUP_TAG_FILE="__xplan_design_app_environment.back"
export REACTOR_BACKUP_TAG_FILE="__xplan_reactor_environment.back"