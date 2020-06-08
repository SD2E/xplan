import json
import os
from xplan_design.experiment_design import ExperimentDesign

from xplan_submit.lab.strateos.write_parameters import design_to_parameters

transcriptic_cfg = {
  "analytics": True,
  "api_root": "https://secure.transcriptic.com",
  "email": "dbryce@sift.net",
  "feature_groups": [],
  "organization_id": "sd2org",
  "token": "F8bPPxtAxLxgknrRnrya",
  "user_id": "u1bqt2nyk66zd"
}

def test_submit_growth_curve():
    design_file = os.path.join(os.path.curdir, "../resources/YEAST_STATES/experiments//experiment.transcriptic.2020-05-04-YeastSTATES-1-0-Growth-Curves/design_experiment.transcriptic.2020-05-04-YeastSTATES-1-0-Growth-Curves.json")
    request_file = os.path.join(os.path.curdir, "../resources/YEAST_STATES/experiments//experiment.transcriptic.2020-05-04-YeastSTATES-1-0-Growth-Curves/request_experiment.transcriptic.2020-05-04-YeastSTATES-1-0-Growth-Curves.json")
    out_dir = os.path.join(os.path.curdir, "../test_out")
    if not os.path.exists(out_dir):
        os.mkdir(out_dir)
    with open(design_file, "r") as design:
        experiment_json = json.load(design)
        experiment_design = ExperimentDesign(**experiment_json)
        with open(request_file) as request:
            experiment_request = json.load(request)
            design_to_parameters(experiment_request,
                                 experiment_design,
                                 transcriptic_cfg,
                                 out_dir=out_dir)