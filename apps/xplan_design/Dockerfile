FROM ubuntu:bionic

RUN apt-get update
RUN apt-get install -y python-pip

ADD xplan-dev-env/xplan-models /xplan-models
RUN pip install /xplan_models
RUN rm -rf /xplan_models

ADD . /xplan_design
RUN pip install /xplan_design
RUN rm -rf /xplan_design