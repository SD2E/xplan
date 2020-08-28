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

all: build test deploy

build: build-xplan-design-app

test: test-apps test-components

test-apps: test-xplan-design-app

build-xplan-design-app:
	cp -r components/xplan_design apps/xplan_design
	cp -r xplan-dev-env/xplan_models apps/xplan_design
	cp -r components/xplan_utils apps/xplan_design
	docker build -f apps/xplan_design/Dockerfile -t ${DESIGN_APP_TAG} apps/xplan_design
	rm -rf apps/xplan_design/xplan_design
	rm -rf apps/xplan_design/xplan_models
	rm -rf apps/xplan_design/xplan_utils

test-xplan-design-app: build-xplan-design-app test-xplan-design-app-local

test-xplan-design-app-local: build-xplan-design-app
	sh scripts/run_docker.sh ${TMP_OUT} ${DESIGN_APP_TAG} invocation_experiment.transcriptic.2020-05-04-YeastSTATES-1-0-Growth-Curves.json

test-xplan-design-app-remote: deploy-xplan-design-app
	tapis auth init
	sh scripts/run_tapis_app.sh ${REMOTE_WORK_DIR}


test-components:

deploy: build deploy-apps deploy-reactors

deploy-apps: deploy-xplan-design-app

deploy-reactors: deploy-xplan-reactor

deploy-xplan-design-app: clean-deploy-xplan-design-app  build-xplan-design-app
	## tapis requires that docker build context is the same as the working directory
	ln -s apps/xplan_design/assets/ assets
	cp -r xplan-dev-env/xplan_models apps/xplan_design
	cp -r components/xplan_utils apps/xplan_design
	cp -r components/xplan_design apps/xplan_design
	tapis app deploy -W apps/xplan_design
	rm -rf apps/xplan_design/xplan_models
	rm -rf apps/xplan_design/xplan_utils
	rm -rf apps/xplan_design/xplan_design
	rm assets
	docker push ${DESIGN_APP_TAG}

clean-deploy: clean-deploy-xplan-design-app

clean-deploy-xplan-design-app:
	rm assets || true
	rm apps/xplan_design/assets/assets || true

deploy-xplan-reactor:
	scripts/create_reactor_if_not_exists.sh

test-xplan-reactor-remote: deploy-xplan-design-app deploy-xplan-reactor
	scripts/run_reactor.sh