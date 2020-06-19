FROM sd2e/python3:latest

RUN pip3 install --upgrade pip

ADD ./xplan_models /xplan_models
RUN pip3 install /xplan_models
RUN rm -rf /xplan_models

ADD ./xplan_utils /xplan_utils
RUN pip3 install /xplan_utils
RUN rm -rf /xplan_utils

ADD ./xplan_design /xplan_design
#RUN pip3 install /xplan_design
RUN cd /xplan_design && python3 setup.py install && cd /
RUN rm -rf /xplan_design


ADD run.py /run.py

ENTRYPOINT [ "python3", "/run.py" ]