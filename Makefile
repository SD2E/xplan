include .environment
TMP_OUT?=${PWD}/out

# make these variables from .environment available
export XPLAN_USER
export XPLAN_EMAIL
export XPLAN_DOCKER_NAMESPACE
export REMOTE_WORK_DIR
export APP_NAME
export APP_DEPLOYMENT_SYSTEM
export APP_EXECUTION_SYSTEM
export APP_VERSION
export APP_DOCKER_NAMESPACE
export APP_DOCKER_REPO
export APP_DOCKER_TAG
export REACTOR_NAME
export REACTOR_ALIAS
export REACTOR_DOCKER_HUB_ORG
export REACTOR_DOCKER_IMAGE_TAG
export REACTOR_DOCKER_IMAGE_VERSION

export APP_CONTAINER_FULL_NAME=${APP_DOCKER_NAMESPACE}/${APP_DOCKER_REPO}:${APP_DOCKER_TAG}
export REACTOR_CONTAINER_FULL_NAME=${REACTOR_DOCKER_HUB_ORG}/${REACTOR_DOCKER_IMAGE_TAG}:${REACTOR_DOCKER_IMAGE_VERSION}
export XPLAN_DESIGN_APP_ID="${APP_NAME}-${APP_VERSION}"

all: build test deploy

build: build-xplan-design-app

test: test-apps test-components

test-apps: test-xplan-design-app

build-xplan-design-app:
	scripts/build_design_app.sh

test-xplan-design-app: build-xplan-design-app test-xplan-design-app-local

test-xplan-design-app-local: build-xplan-design-app
	sh scripts/run_docker.sh ${TMP_OUT} ${APP_CONTAINER_FULL_NAME} invocation_experiment.transcriptic.2020-05-04-YeastSTATES-1-0-Growth-Curves.json

test-xplan-design-app-remote: deploy-xplan-design-app
	tapis auth init
	sh scripts/run_tapis_app.sh ${REMOTE_WORK_DIR}


test-components:

deploy: build deploy-apps deploy-reactors

deploy-apps: deploy-xplan-design-app

deploy-reactors: deploy-xplan-reactor

deploy-xplan-design-app: clean-deploy-xplan-design-app  build-xplan-design-app
	scripts/deploy_design_app.sh

clean-deploy: clean-deploy-xplan-design-app

clean-deploy-xplan-design-app:
	rm assets || true
	rm apps/xplan_design/assets/assets || true

deploy-xplan-reactor:
	scripts/create_reactor_if_not_exists.sh

test-xplan-reactor-remote: deploy-xplan-design-app deploy-xplan-reactor
	scripts/run_reactor.sh