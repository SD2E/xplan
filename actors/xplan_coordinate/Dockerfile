FROM sd2e/reactors:python3-edge

RUN pip install --no-cache-dir agavepy==0.9.3

ADD ./xplan_coordinate_reactor /xplan_coordinate_reactor

## Replace the design app id in the reactor, so it points to the correct app
ENV XPLAN_DESIGN_APP_ID="jladwig_xplan2_design-0.0.1"
RUN sed -i "s@jladwig_xplan2_design-0.0.1@${XPLAN_DESIGN_APP_ID}@g" /xplan_coordinate_reactor/src/xplan_coordinate_reactor/messagetypes/xplandesignmessage.py

# FIXME this is more the "reactor archive system" than "app deployment system"
# but I am currently forcing it to use the app deployment system until we
# see reason for doing otherwise
ENV APP_DEPLOYMENT_SYSTEM="data-tacc-work-jladwig"
RUN sed -i "s@data-tacc-work-jladwig@${APP_DEPLOYMENT_SYSTEM}@g" /xplan_coordinate_reactor/src/xplan_coordinate_reactor/messagetypes/xplandesignmessage.py

ENV REACTOR_BASE_PATH="xplan2"
RUN sed -i "s@\"archivePath\": \"xplan2@\"archivePath\": \"${REACTOR_BASE_PATH}@g" /xplan_coordinate_reactor/src/xplan_coordinate_reactor/messagetypes/xplandesignmessage.py

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