FROM sd2e/reactors:python3-edge

RUN pip install --no-cache-dir agavepy==0.9.3

ADD ./xplan_coordinate_reactor /xplan_coordinate_reactor
RUN pip3 install --no-cache-dir /xplan_coordinate_reactor \
    && rm -rf /xplan_coordinate_reactor

ADD ./xplan_models /xplan_models
RUN pip3 install --no-cache-dir /xplan_models \
    && rm -rf /xplan_models

ADD ./xplan_design /xplan_design
RUN pip3 install --no-cache-dir /xplan_design \
    && rm -rf /xplan_design

ADD ./xplan_utils /xplan_utils
RUN pip3 install --no-cache-dir /xplan_utils \
    && rm -rf /xplan_utils

ADD ./xplan_submit /xplan_submit
RUN pip3 install --no-cache-dir /xplan_submit \
    && rm -rf /xplan_submit