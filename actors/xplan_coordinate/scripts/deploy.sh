#!/usr/bin/env bash

set -e 

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
$DIR/build.sh
$DIR/push.sh
$DIR/make-actor.sh
echo "New xplan coordinate actor deployed. Remember to delete old ones..."
