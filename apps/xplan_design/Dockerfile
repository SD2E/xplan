FROM sd2e/python3:latest

#RUN pip3 install --upgrade pip
RUN pip3 install pandas
RUN pip install transcriptic==9.1.0 --upgrade
RUN pip3 install jsonpatch

# RUN pip3 install --upgrade setuptools
RUN pip3 install git+https://github.com/SD2E/synbiohub_adapter.git@v1.3

RUN pip3 install pysmt
RUN pysmt-install --z3 --confirm-agreement
ENV PYSMT_CYTHON=0
# RUN cd /xplan_design && python3 setup.py install && cd /

RUN pip3 install cython

ADD ./xplan_models /xplan_models
RUN pip3 install /xplan_models
RUN rm -rf /xplan_models

ADD ./xplan_utils /xplan_utils
RUN pip3 install /xplan_utils
RUN rm -rf /xplan_utils

ADD ./xplan_design /xplan_design
RUN pip3 install /xplan_design
RUN rm -rf /xplan_design


ADD run.py /run.py

ENTRYPOINT [ "python3", "/run.py" ]