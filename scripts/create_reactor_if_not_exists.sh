# Return the id of a reactor if it exists
REACTOR_NAME=$1
XPLAN_DESIGN_APP_ID=$2

ACTOR_ID=`tapis actors list | grep ${REACTOR_NAME} | cut -f 2 -d "|"`

if [ -z ${ACTOR_ID} ]; then

  CONTAINER_FULL_NAME=${DOCKER_HUB_ORG}/${DOCKER_IMAGE_TAG}:${DOCKER_IMAGE_VERSION}
  echo "tapis actors create --repo ${CONTAINER_FULL_NAME} \
                      --stateful \
                      -n ${REACTOR_NAME}"
  tapis actors create --repo ${CONTAINER_FULL_NAME} \
                      --stateful \
                      -n ${REACTOR_NAME}
  ACTOR_ID=`tapis actors list | grep ${REACTOR_NAME} | cut -f 2 -d "|"`

fi

OLD_DIR=`pwd`
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
echo "cd ${DIR}/../actors/xplan_coordinate"
cd ${DIR}/../actors/xplan_coordinate

## abaco won't pass along build args, so have to sed in the arg value into the Dockerfile
cp Dockerfile Dockerfile.back
echo $XPLAN_DESIGN_APP_ID
echo "sed -i "s@XPLAN_DESIGN_APP_ID=['\"]jladwig_xplan_design-0.0.1['\"]@XPLAN_DESIGN_APP_ID=\"${XPLAN_DESIGN_APP_ID}\"@g" Dockerfile
"
sed -i "s@XPLAN_DESIGN_APP_ID=['\"]jladwig_xplan_design-0.0.1['\"]@XPLAN_DESIGN_APP_ID=\"${XPLAN_DESIGN_APP_ID}\"@g" Dockerfile
cat Dockerfile
cp -r $DIR/../xplan-dev-env/xplan_models ./xplan_models
cp -r $DIR/../components/xplan_utils ./xplan_utils
cp -r $DIR/../components/xplan_design ./xplan_design
cp -r $DIR/../components/xplan_submit ./xplan_submit
abaco deploy -p -U ${ACTOR_ID} -F Dockerfile
rm -rf ./xplan_models
rm -rf ./xplan_utils
rm -rf ./xplan_design
rm -rf ./xplan_submit
mv Dockerfile.back Dockerfile


cd ${OLD_DIR}