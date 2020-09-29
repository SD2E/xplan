import json
from xplan_utils.helpers import get_experiment_request
from xplan_design.design import generate_design
import os

def gen_design(experiment_id,
               challenge_problem="YEAST_STATES",
               input_dir="../resources",
               out_dir="../test_out"):
    transcriptic_cfg = os.path.join(os.path.curdir, "../../../../secrets/tx_secrets.json")

    if not os.path.exists(out_dir):
        os.mkdir(out_dir)

    with open(transcriptic_cfg, "r") as tx_secret:
        generate_design(experiment_id, challenge_problem, json.load(tx_secret),
                        input_dir=input_dir, out_dir=out_dir)


def test_generate_timeseries_design():
    experiment_id = "experiment.transcriptic.2020-03-06-YeastSTATES-Beta-Estradiol-OR-Gate-Plant-TF-Dose-Response"
    gen_design(experiment_id)

def test_generate_round_1_1_design():
    experiment_id = "experiment.transcriptic.2020-08-28-YeastSTATES-1-0-Time-Series-Round-1-1"
    gen_design(experiment_id)

def test_generate_timeseries_dr_design():
    experiment_id = "experiment.transcriptic.2020-03-06-YeastSTATES-Beta-Estradiol-OR-Gate-Plant-TF-Dose-Response"
    gen_design(experiment_id)

def test_generate_timeseries_design():
    experiment_id = "experiment.transcriptic.2020-08-08-Plan-Requirements-UCSB-B-subtilis-CitT-PFA-TimeSeriesTitration-Strateos"
    input_dir = "../resources/NOVEL_CHASSIS",
    out_dir = "../test_out/NOVEL_CHASSIS"
    gen_design(experiment_id, challenge_problem="NOVEL_CHASSIS", input_dir=input_dir, out_dir=out_dir)

def test_generate_timeseries_design_small():
    experiment_id = "experiment.transcriptic.2020-08-08-Plan-Requirements-UCSB-B-subtilis-CitT-PFA-TimeSeriesTitration-Strateos-small"
    input_dir = "../resources/NOVEL_CHASSIS",
    out_dir = "../test_out/NOVEL_CHASSIS"
    gen_design(experiment_id, challenge_problem="NOVEL_CHASSIS", input_dir=input_dir, out_dir=out_dir)

def test_generate_timeseries_nissle_design():
    experiment_id = "experiment.transcriptic.2020-08-12-Plan-Requirements-UCSB-E-coli-nissle-antibiotic-TimeSeriesTitration-Strateos"
    input_dir = "../resources/NOVEL_CHASSIS",
    out_dir = "../test_out/NOVEL_CHASSIS"
    gen_design(experiment_id, challenge_problem="NOVEL_CHASSIS", input_dir=input_dir, out_dir=out_dir)

def test_generate_live_dead_backpatch_design():
    experiment_id = "experiment.transcriptic.2020-08-27-Strateos-YeastSTATES-Ethanol-Sytox-LiveDeadClassification"
    gen_design(experiment_id)

def test_generate_growth_curve_design():
    experiment_id = "experiment.transcriptic.2020-05-04-YeastSTATES-1-0-Growth-Curves"
    gen_design(experiment_id)


def test_generate_round2_design():
    experiment_id = "experiment.transcriptic.2020-09-29-YeastSTATES-1-0-Time-Series-Round-2-0"
    gen_design(experiment_id)