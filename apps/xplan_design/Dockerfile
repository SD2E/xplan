FROM sd2e/python3:latest

RUN pip3 install --upgrade pip

ADD xplan-dev-env/xplan_models /xplan_models
RUN pip3 install /xplan_models
RUN rm -rf /xplan_models

ADD components/xplan_design /xplan_design
RUN pip3 install -e /xplan_design
RUN rm -rf /xplan_design

ADD components/xplan_utils /xplan_utils
RUN pip3 install -e /xplan_utils
RUN rm -rf /xplan_utils

ADD apps/xplan_design/run.py /run.py