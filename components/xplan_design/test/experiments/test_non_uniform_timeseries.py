import json

from xplan_design.design import generate_design
import os



def test_generate_timeseries_design():
    invocation_file = os.path.join(os.path.curdir, "../resources/invocation_experiment.transcriptic.2020-08-08-Plan-Requirements-UCSB-B-subtilis-CitT-PFA-TimeSeriesTitration-Strateos.json")
    transcriptic_cfg = os.path.join(os.path.curdir, "../../../../secrets/tx_secrets.json")
    out_dir = os.path.join(os.path.curdir, "../test_out")
    if not os.path.exists(out_dir):
        os.mkdir(out_dir)
    with open(invocation_file, "r") as experiment_request, open(transcriptic_cfg, "r") as tx_secret:
        generate_design(json.load(experiment_request), json.load(tx_secret), out_dir)

def test_generate_timeseries_design_small():
    invocation_file = os.path.join(os.path.curdir, "../resources/invocation_experiment.transcriptic.2020-08-08-Plan-Requirements-UCSB-B-subtilis-CitT-PFA-TimeSeriesTitration-Strateos-small.json")
    transcriptic_cfg = os.path.join(os.path.curdir, "../../../../secrets/tx_secrets.json")
    out_dir = os.path.join(os.path.curdir, "../test_out")
    if not os.path.exists(out_dir):
        os.mkdir(out_dir)
    with open(invocation_file, "r") as experiment_request, open(transcriptic_cfg, "r") as tx_secret:
        generate_design(json.load(experiment_request), json.load(tx_secret), out_dir)