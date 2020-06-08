import json

from xplan_design.design import generate_design
import os


xplan_config = {
#  "upload" : False,
#  "overwrite": False,
  "state_file": "state.json",
  "out_dir": "/work/projects/SD2E-Community/prod/projects/sd2e-project-14/xplan-reactor"
}

transcriptic_cfg = {
  "analytics": True,
  "api_root": "https://secure.transcriptic.com",
  "email": "dbryce@sift.net",
  "feature_groups": [],
  "organization_id": "sd2org",
  "token": "F8bPPxtAxLxgknrRnrya",
  "user_id": "u1bqt2nyk66zd"
}

def test_generate_growth_curve_design():
    invocation_file = os.path.join(os.path.curdir, "../resources/invocation_experiment.transcriptic.2020-05-04-YeastSTATES-1-0-Growth-Curves.json")
    out_dir = os.path.join(os.path.curdir, "../test_out")
    if not os.path.exists(out_dir):
        os.mkdir(out_dir)
    with open(invocation_file, "r") as experiment_request:
        generate_design(json.load(experiment_request), xplan_config, transcriptic_cfg, out_dir)