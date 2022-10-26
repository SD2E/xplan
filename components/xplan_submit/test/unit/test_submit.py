import json
import os
from xplan_submit.lab.strateos.submit import submit_experiment

xplan_config = {
#  "upload" : False,
#  "overwrite": False,
  "state_file": "state.json",
  "out_dir": "/work/projects/SD2E-Community/prod/projects/sd2e-project-14/xplan-reactor"
}

transcriptic_params = {
    "default" : "XPlanAutomatedExecutionTest",
  "projects" : {
  "XPlanAutomatedExecutionTest" : {
      "id" : "p1bqm3ehqzgum",
      "nick" : "Yeast Gates"
}
  }}

def submit(experiment_id,
           input_dir = "../resources/",
           challenge_problem="YEAST_STATES",
           out_dir="../test_out"):
    transcriptic_cfg = os.path.join(os.path.curdir, "../../../../secrets/tx_secrets.json")

    if not os.path.exists(out_dir):
        os.mkdir(out_dir)

    with open(transcriptic_cfg, "r") as tx_secret:
        #submit_experiment(experiment_request, xplan_config, json.load(tx_secret), transcriptic_params, out_dir=out_dir)
        submit_experiment(experiment_id,
                          challenge_problem,
                          json.load(tx_secret),
                          transcriptic_params,
                          input_dir=input_dir,
                          out_dir=out_dir)

def test_submit_growth_curve():
    experiment_id = "experiment.transcriptic.2020-05-04-YeastSTATES-1-0-Growth-Curves"
    submit(experiment_id)

def test_submit_round_1_1():
    experiment_id = "experiment.transcriptic.2020-08-28-YeastSTATES-1-0-Time-Series-Round-1-1"
    submit(experiment_id)

def test_submit_cell_free_riboswitches():
    experiment_id = "experiment.transcriptic.2020-09-23-Cell-Free-Transcriptional-Riboswitch-Characterization-Strateos"
    challenge_problem = "CELL_FREE_RIBOSWITCHES"
    submit(experiment_id, challenge_problem=challenge_problem)