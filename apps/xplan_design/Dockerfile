FROM sd2e/python3:latest

ADD xplan-dev-env/xplan_models /xplan_models
RUN pip3 install /xplan_models
RUN rm -rf /xplan_models

ADD components/xplan_design /xplan_design
RUN pip3 install /xplan_design
#RUN rm -rf /xplan_design

ADD apps/xplan_design/run.py /run.py