import argparse
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
    parser.add_argument('lab_configuration', help='Lab LIMS credentials')
    parser.add_argument("out_dir", help="Base directory for output", default=".")
    return parser

def run(args):
    experiment_id = args.experiment_id
    challenge_problem = args.challenge_problem
    lab_configuration = args.lab_configuration
    out_dir = args.out_dir
    #out_dir = "/work/projects/SD2E-Community/prod/projects/sd2e-project-14/xplan-reactor"

    with open(lab_configuration, "r") as lab_secret:
        generate_design(experiment_id, challenge_problem, json.load(lab_secret),
                        input_dir=out_dir, out_dir=out_dir)

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

def cleanup(out):
    print("Cleaning up...")
    print("  Removing unwanted out_dir files...")
    cleanup_dir(os.path.join(out, 'archive'), prefix_offset=4)
    cleanup_dir(os.path.join(out, 'secrets'), prefix_offset=4)
    cleanup_dir(os.path.join(out, 'test'), prefix_offset=4)
    cleanup_file('tx_secrets.json', prefix_offset=4)

def read_state(path: str) -> str:
    res = {}
    if os.path.exists(path):
        with open(path, 'r') as state:
            res = json.load(state)
    return res

def main():
    try:
        parser = _parser()
        args = parser.parse_args()

        # ensure the logger is configured
        h1 = logging.StreamHandler(sys.stdout)
        h1.setLevel(logging.DEBUG)
        h1.addFilter(lambda record: record.levelno <= logging.INFO)
        h2 = logging.StreamHandler(sys.stderr)
        h2.setLevel(logging.WARNING)
        logging.basicConfig(handlers = [h1, h2], format='%(levelname)s:%(message)s')

        state_path = os.path.join(args.out_dir, args.challenge_problem, "state.json")
        state_before = read_state(state_path)
        run(args)
        state_after = read_state(state_path)
        state_diff = jsonpatch.make_patch(state_before, state_after)

        print("State before: {}".format(state_before))
        print("State after: {}".format(state_after))
        print("State diff: {}".format(state_diff))
        with open('state.diff', 'w') as f:
            f.write(state_diff.to_string())
    finally:
        cleanup(args.out_dir)
        logging.shutdown()


if __name__ == '__main__':
    main()
