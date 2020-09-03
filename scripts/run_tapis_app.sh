REMOTE_WORKDIR=$1

tapis files mkdir agave://${REMOTE_WORKDIR} xplan2/YEAST_STATES/experiments/experiment.transcriptic.2020-05-04-YeastSTATES-1-0-Growth-Curves
tapis files upload agave://${REMOTE_WORKDIR}/xplan2/YEAST_STATES/experiments/experiment.transcriptic.2020-05-04-YeastSTATES-1-0-Growth-Curves components/xplan_design/test/resources/YEAST_STATES/experiments/experiment.transcriptic.2020-05-04-YeastSTATES-1-0-Growth-Curves/request_experiment.transcriptic.2020-05-04-YeastSTATES-1-0-Growth-Curves.json

tapis files mkdir agave://${REMOTE_WORKDIR}/xplan2 secrets
tapis files upload agave://${REMOTE_WORKDIR}/xplan2/secrets secrets/tx_secrets.json

tapis jobs submit -F apps/xplan_design/job.json
