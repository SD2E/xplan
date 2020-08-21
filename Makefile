DESIGN_APP_TAG=jladwigsift/xplan:2.0
XPLAN_DESIGN_APP_ID=xplan_design-0.0.1
TMP_OUT=${PWD}/out
REMOTE_WORK_DIR=data-tacc-work-jladwig

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

deploy: deploy-apps

deploy-apps: deploy-xplan-design-app

deploy-xplan-design-app: clean-deploy-xplan-design-app
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

clean-deploy: clean-deploy-xplan-design-app

clean-deploy-xplan-design-app:
	rm assets || true
	rm apps/xplan_design/assets/assets || true
