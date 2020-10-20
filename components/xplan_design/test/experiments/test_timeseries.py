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
    gen_design(experiment_id, challenge_problem="NOVEL_CHASSIS")

def test_generate_timeseries_design_small():
    experiment_id = "experiment.transcriptic.2020-08-08-Plan-Requirements-UCSB-B-subtilis-CitT-PFA-TimeSeriesTitration-Strateos-small"
    gen_design(experiment_id, challenge_problem="NOVEL_CHASSIS")

def test_generate_timeseries_nissle_design():
    experiment_id = "experiment.transcriptic.2020-08-12-Plan-Requirements-UCSB-E-coli-nissle-antibiotic-TimeSeriesTitration-Strateos"
    gen_design(experiment_id, challenge_problem="NOVEL_CHASSIS")


def test_generate_timeseries_nissle_rerun_design():
    experiment_id = "experiment.transcriptic.2020-10-22-Plan-Requirements-UCSB-E-coli-nissle-antibiotic-rerun-TimeSeriesTitration-Strateos"
    gen_design(experiment_id, challenge_problem="NOVEL_CHASSIS")



def test_generate_timeseries_protogens_design():
    experiment_id = "experiment.transcriptic.2020-08-12-Plan-Requirements-UCSB-P-protegens-PF5-antibiotic-TimeSeriesTitration-Strateos"
    gen_design(experiment_id, challenge_problem="NOVEL_CHASSIS")

def test_generate_live_dead_backpatch_design():
    experiment_id = "experiment.transcriptic.2020-08-27-Strateos-YeastSTATES-Ethanol-Sytox-LiveDeadClassification"
    gen_design(experiment_id)

def test_generate_growth_curve_design():
    experiment_id = "experiment.transcriptic.2020-05-04-YeastSTATES-1-0-Growth-Curves"
    gen_design(experiment_id)

def test_generate_cell_free_riboswitches_design():
    experiment_id = "experiment.transcriptic.2020-09-23-Cell-Free-Transcriptional-Riboswitch-Characterization-Strateos"
    challenge_problem = "CELL_FREE_RIBOSWITCHES"
    gen_design(experiment_id, challenge_problem=challenge_problem)

def test_generate_cell_free_riboswitches_auto_design():
    experiment_id = "experiment.transcriptic.2020-10-13-Test-Cell-Free-Transcriptional-Riboswitch-Characterization"
    challenge_problem = "CELL_FREE_RIBOSWITCHES"
    gen_design(experiment_id, challenge_problem=challenge_problem)

def test_generate_cell_free_riboswitches_1_32_design():
    experiment_id = "experiment.transcriptic.2020-10-16-Cell-Free-Transcriptional-Riboswitch-Characterization-Sequences-1-32"
    challenge_problem = "CELL_FREE_RIBOSWITCHES"
    gen_design(experiment_id, challenge_problem=challenge_problem)


def test_generate_round2_design():
    experiment_id = "experiment.transcriptic.2020-09-29-YeastSTATES-1-0-Time-Series-Round-2-0"
    gen_design(experiment_id)