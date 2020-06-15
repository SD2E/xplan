DESIGN_APP_TAG="sd2e/xplan:2.0"
XPLAN_DESIGN_APP_ID="xplan_design-0.0.1"

all: build test deploy

build: build-xplan-design-app

test: test-apps test-components

test-apps: test-xplan-design-app

build-xplan-design-app:
	docker build -f apps/xplan_design/Dockerfile -t ${DESIGN_APP_TAG} .

test-xplan-design-app: build-xplan-design-app test-xplan-design-app-local

test-xplan-design-app-local: build-xplan-design-app
	docker run -t ${DESIGN_APP_TAG}

test-xplan-design-app-remote: build-xplan-design-app deploy-xplan-design-app
	tapis jobs submit -F apps/xplan_design/job.json


test-components:

deploy: deploy-apps

deploy-apps: deploy-xplan-design-app

deploy-xplan-design-app: clean-deploy-xplan-design-app
	ln -s apps/xplan_design/assets/ assets
	tapis apps deploy -W apps/xplan_design
	rm assets

clean-deploy: clean-deploy-xplan-design-app

clean-deploy-xplan-design-app:
	rm assets || true
	rm apps/xplan_design/assets/assets || true
