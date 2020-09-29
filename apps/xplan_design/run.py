import argparse
import base64
import json
import jsonpatch
import logging
import os
import shutil
import sys
from xplan_design.design import generate_design

def _parser():
    parser = argparse.ArgumentParser(description='XPlan Generate Design')
    parser.add_argument('experiment_id', help='Experiment ID')
    parser.add_argument('challenge_problem', help='Challenge Problem')
    parser.add_argument("out_path", help="Base directory for output", default=".")
    parser.add_argument("experiment_dir", help="Experiment directory for input")
    parser.add_argument("state_json", help="Path to state json")
    parser.add_argument('--lab_configuration', help='Lab LIMS credentials')
    parser.add_argument('--lab_configuration_uri', help='Lab LIMS credentials')
    return parser


def cleanup_dir(path, *, prefix_str = ' ', prefix_step = 2, prefix_offset = 0):
    prefix = prefix_str*prefix_offset
    print("{}{}".format(prefix, path))
    prefix += prefix_str*prefix_step
    if not os.path.exists(path):
        print("{}Failed to remove {}. Does not exist.".format(prefix, path))
        return
    if not os.path.isdir(path):
        print("{}Failed to remove {}. Not a directory.".format(prefix, path))
        return
    shutil.rmtree(path)
    print("{}Removed directory: {}".format(prefix, path))

def cleanup_file(path, *, prefix_str = ' ', prefix_step = 2, prefix_offset = 0):
    prefix = prefix_str*prefix_offset
    print("{}{}".format(prefix, path))
    prefix += prefix_str*prefix_step
    if not os.path.exists(path):
        print("{}Failed to remove {}. Does not exist.".format(prefix, path))
        return
    if not os.path.isfile(path):
        print("{}Failed to remove {}. Not a file".format(prefix, path))
        return
    os.remove(path)
    print("{}Removed file: {}".format(prefix, path))

def cleanup():
    print("Cleaning up...")
    print("  Removing secrets file...")
    cleanup_file('tx_secrets.json', prefix_offset=4)

def read_state(path: str) -> str:
    res = {}
    if os.path.exists(path):
        with open(path, 'r') as state:
            res = json.load(state)
    return res

def main():
    try:
        # ensure the logger is configured
        h1 = logging.StreamHandler(sys.stdout)
        h1.setLevel(logging.DEBUG)
        h1.addFilter(lambda record: record.levelno <= logging.INFO)
        h2 = logging.StreamHandler(sys.stderr)
        h2.setLevel(logging.WARNING)
        logging.basicConfig(handlers = [h1, h2], format='%(levelname)s:%(message)s')

        print("Parsing args...")
        parser = _parser()
        args = parser.parse_args()
        if args.lab_configuration is not None:
            lc = base64.b64decode(args.lab_configuration.encode('ascii')).decode('ascii')
            lab_secret = json.loads(lc)
        elif args.lab_configuration_uri is not None:
            lc = args.lab_configuration_uri
            with open(lc, "r") as f:
                lab_secret = json.load(f)
        else:
            raise Exception("lab_configuration must be provided")

        experiment_id = args.experiment_id
        experiment_in_dir = args.experiment_dir
        challenge_problem = args.challenge_problem
        out_dir = args.out_path
        state_in_path = args.state_json
        # state_in_path = 'state.json'

        # copy the input into the output
        challenge_dir = os.path.join(out_dir, challenge_problem)
        experiments_dir = os.path.join(challenge_dir, 'experiments')
        os.makedirs(experiments_dir)
        experiment_out_dir = os.path.join(experiments_dir, experiment_id)
        shutil.copytree(experiment_in_dir, experiment_out_dir)
        shutil.move(state_in_path, os.path.join(challenge_dir, 'state.json'))

        print("challenge_dir = {}".format(challenge_dir))
        print("experiment_out_dir = {}".format(experiment_out_dir))
        print("out_dir = {}".format(out_dir))
        print("state_in_path = {}".format(state_in_path))

        state_path = os.path.join(out_dir, challenge_problem, "state.json")
        state_before = read_state(state_path)
        
        generate_design(experiment_id, challenge_problem, lab_secret,
                        input_dir=out_dir, out_dir=out_dir)

        state_after = read_state(state_path)
        state_diff = jsonpatch.make_patch(state_before, state_after)

        print("State before: {}".format(state_before))
        print("State after: {}".format(state_after))
        print("State diff: {}".format(state_diff))
        with open('state.diff', 'w') as f:
            f.write(state_diff.to_string())
    finally:
        cleanup()
        logging.shutdown()


if __name__ == '__main__':
    main()
