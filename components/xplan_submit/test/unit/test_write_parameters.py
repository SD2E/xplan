import json
import os
from xplan_design.experiment_design import ExperimentDesign
from xplan_utils.helpers import get_experiment_design, get_experiment_request
from xplan_submit.lab.strateos.write_parameters import design_to_parameters

def write_params(experiment_id, input_dir = "../resources", challenge_problem="YEAST_STATES", out_dir="../test_out"):
    transcriptic_cfg = os.path.join(os.path.curdir, "../../../../secrets/tx_secrets.json")

    if not os.path.exists(out_dir):
        os.mkdir(out_dir)

    with open(transcriptic_cfg, "r") as tx_secret:
        design_to_parameters(experiment_id,
                             challenge_problem,
                             json.load(tx_secret),
                             input_dir=input_dir,
                             out_dir=out_dir)



def test_submit_growth_curve():
    experiment_id = "experiment.transcriptic.2020-05-04-YeastSTATES-1-0-Growth-Curves"
    write_params(experiment_id)

def test_write_round_1_1():
    experiment_id = "experiment.transcriptic.2020-08-28-YeastSTATES-1-0-Time-Series-Round-1-1"
    write_params(experiment_id)

def test_write_dr_params():
    experiment_id = "experiment.transcriptic.2020-03-06-YeastSTATES-Beta-Estradiol-OR-Gate-Plant-TF-Dose-Response"
    write_params(experiment_id)

def test_write_cell_free_riboswitches_params():
    experiment_id = "experiment.transcriptic.2020-09-23-Cell-Free-Transcriptional-Riboswitch-Characterization-Strateos"
    challenge_problem = "CELL_FREE_RIBOSWITCHES"
    write_params(experiment_id, challenge_problem=challenge_problem)

def test_write_cell_free_riboswitches_1_32_params():
    experiment_id = "experiment.transcriptic.2020-10-16-Cell-Free-Transcriptional-Riboswitch-Characterization-Sequences-1-32"
    challenge_problem = "CELL_FREE_RIBOSWITCHES"
    write_params(experiment_id, challenge_problem=challenge_problem)

def test_write_NC_endogenous_promoter_params():
    experiment_id = "experiment.transcriptic.2020-12-04-NovelChassis-Endogenous-Promoter-Yellow-41-48"
    challenge_problem = "NOVEL_CHASSIS"
    write_params(experiment_id, challenge_problem=challenge_problem)