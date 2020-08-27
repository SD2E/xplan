FROM sd2e/reactors:python3-edge

RUN pip install --no-cache-dir agavepy==0.9.3

ADD ./xplan_coordinate_reactor /xplan_coordinate_reactor

## Replace the design app id in the reactor, so it points to the correct app

ENV XPLAN_DESIGN_APP_ID="xplan_design-0.0.1"
RUN sed -i "s@jladwig_xplan_design-0.0.1@${XPLAN_DESIGN_APP_ID}@g" /xplan_coordinate_reactor/src/xplan_coordinate_reactor/messagetypes/xplandesignmessage.py


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