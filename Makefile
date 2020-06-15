DESIGN_APP_TAG="sd2e/xplan:2.0"

all: build test deploy

build: build-xplan-design-app

test: test-apps test-components

test-apps: test-xplan-design-app

build-xplan-design-app:
	docker build -f apps/xplan_design/Dockerfile -t ${DESIGN_APP_TAG} .

test-xplan-design-app: build-xplan-design-app
	docker run -t ${DESIGN_APP_TAG}

test-components:

deploy: deploy-apps

deploy-apps: deploy-xplan-design-app

deploy-xplan-design-app:
	tapis apps deploy -W apps/xplan_design