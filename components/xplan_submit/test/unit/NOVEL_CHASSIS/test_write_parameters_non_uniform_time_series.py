import json
import os
from xplan_design.experiment_design import ExperimentDesign
from xplan_utils.helpers import get_experiment_design, get_experiment_request

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

def write_parameters(experiment_id, input_dir):
    out_dir = os.path.join(os.path.curdir, "../test_out")
    if not os.path.exists(out_dir):
        os.mkdir(out_dir)

    experiment_design = get_experiment_design(experiment_id, input_dir)
    experiment_request = get_experiment_request(experiment_id, input_dir)
    design_to_parameters(experiment_request,
                         experiment_design,
                         transcriptic_cfg,
                         out_dir=out_dir)


def test_write_parameters():
    experiment_id = "experiment.transcriptic.2020-08-08-Plan-Requirements-UCSB-B-subtilis-CitT-PFA-TimeSeriesTitration-Strateos"
    input_dir = "../resources/NOVEL_CHASSIS"
    write_parameters(experiment_id, input_dir)

def test_write_nissle_parameters():
    experiment_id = "experiment.transcriptic.2020-08-12-Plan-Requirements-UCSB-E-coli-nissle-antibiotic-TimeSeriesTitration-Strateos"
    input_dir = "../resources/NOVEL_CHASSIS"
    write_parameters(experiment_id, input_dir)
