import json

from xplan_coordinate.coordinate import coordinate_submission
from xplan_utils.helpers import get_experiment_request
import os

transcriptic_params = {
    "default" : "XPlanAutomatedExecutionTest",
  "projects" : {
  "XPlanAutomatedExecutionTest" : {
      "id" : "p1bqm3ehqzgum",
      "nick" : "Yeast Gates"
}
  }}



def coordinate(experiment_id,
               input_dir="../resources/YEAST_STATES",
               out_dir="../test_out/YEAST_STATES"):
    transcriptic_cfg = os.path.join(os.path.curdir, "../../../../secrets/tx_secrets.json")

    if not os.path.exists(out_dir):
        os.mkdir(out_dir)

    with open(transcriptic_cfg, "r") as tx_secret:
        coordinate_submission(experiment_id, json.load(tx_secret), transcriptic_params, input_dir=input_dir, out_dir=out_dir, mock=False)

def test_coordinate_growth_curve():
    experiment_id = "experiment.transcriptic.2020-05-04-YeastSTATES-1-0-Growth-Curves"
    coordinate(experiment_id)

def test_coordinate_timeseries():
    experiment_id = "experiment.transcriptic.2020-03-06-YeastSTATES-Beta-Estradiol-OR-Gate-Plant-TF-Dose-Response"
    coordinate(experiment_id)

def test_coordinate_round_1_1():
    experiment_id = "experiment.transcriptic.2020-08-28-YeastSTATES-1-0-Time-Series-Round-1-1"
    coordinate(experiment_id)