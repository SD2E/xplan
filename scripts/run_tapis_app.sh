REMOTE_WORKDIR=$1

tapis files mkdir agave://${REMOTE_WORKDIR} xplan2/test/resources
tapis files upload agave://${REMOTE_WORKDIR}/xplan2/test/resources components/xplan_design/test/resources/invocation_experiment.transcriptic.2020-05-04-YeastSTATES-1-0-Growth-Curves.json
tapis jobs submit -F apps/xplan_design/job.json