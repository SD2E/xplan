import json
from xplan_design.design import generate_design
import os
from agavepy import Agave

LOCAL_TMP_DIR="remote_experiments"


class challenge_problems:
    NOVEL_CHASSIS = "NOVEL_CHASSIS"
    RIBOSWITCHES = "RIBOSWITCHES"
    YEAST_STATES = "YEAST_STATES"

CASES = [
    {
        "experiment_id" : "experiment.transcriptic.2021-04-19-Endogenous-Promoter-Yellow-1-10-Run-04",
        "challenge_problem" : challenge_problems.NOVEL_CHASSIS
    },
    {
        "experiment_id" : "experiment.transcriptic.2021-04-19-Cell-Free-Transcriptional-Riboswitch-Characterization-Sequences-33-63A-April-2021",
        "challenge_problem" : challenge_problems.RIBOSWITCHES
    },
    {
        "experiment_id" : "experiment.transcriptic.2021-04-21-YeastSTATES-Dual-Response-CRISPR-Redesigns-Short-Duration-Time-Series-30C",
        "challenge_problem" : challenge_problems.YEAST_STATES
    }

]





def gen_design(experiment_id,
               challenge_problem=challenge_problems.YEAST_STATES,
               input_dir=LOCAL_TMP_DIR,
               out_dir=LOCAL_TMP_DIR):
    transcriptic_cfg = os.path.join(os.path.curdir, "../../../../secrets/tx_secrets.json")

    if not os.path.exists(out_dir):
        os.mkdir(out_dir)

    with open(transcriptic_cfg, "r") as tx_secret:
        generate_design(experiment_id, challenge_problem, json.load(tx_secret),
                        input_dir=input_dir, out_dir=out_dir)

def get_experiment_uri(experiment_id, challenge_problem=challenge_problems.YEAST_STATES):
    source = f"xplan-reactor/{challenge_problem}/experiments/{experiment_id}"
    system_id = "data-sd2e-projects.sd2e-project-14"
    return system_id, source


def get_request(experiment_id, challenge_problem=challenge_problems.YEAST_STATES):
    destDir = f"{LOCAL_TMP_DIR}/{challenge_problem}/experiments/{experiment_id}"
    destFile = os.path.join(destDir, f"request_{experiment_id}.json")
    if not os.path.exists(destDir):
        os.makedirs(destDir)
    elif os.path.exists(destFile):
        return

    system_id, filepath = get_experiment_uri(experiment_id, challenge_problem=challenge_problem)
    ag = Agave.restore()
    files = ag.files.list(systemId=system_id, filePath=filepath)
    request_file = next(iter([ filerecord for filerecord in files if filerecord['name'].startswith("request_") ]))
    assert(request_file)
    response = ag.files.download(systemId=system_id, filePath=request_file['path'])

    with open(destFile, 'wb') as f:
        f.write(response.content)

def test_generate_remote_design():
    case = 2
    experiment_id = CASES[case]['experiment_id']
    challenge_problem = CASES[case]['challenge_problem']
    get_request(experiment_id, challenge_problem=challenge_problem)
    gen_design(experiment_id, challenge_problem=challenge_problem)
