import json

from xplan_design.design import generate_design
import argparse

def _parser():
    parser = argparse.ArgumentParser(description='XPlan Generate Design')
    parser.add_argument('experiment_id', help='Experiment ID')
    parser.add_argument('challenge_problem', help='Challenge Problem')
    parser.add_argument('lab_configuration', help='Lab LIMS credentials')
    parser.add_argument("out_dir", help="Base directory for output", default=".")
    return parser

def main():
    parser = _parser()
    args = parser.parse_args()

    experiment_id = args.experiment_id
    challenge_problem = args.challenge_problem
    lab_configuration = args.lab_configuration
    out_dir = args.out_dir
    #out_dir = "/work/projects/SD2E-Community/prod/projects/sd2e-project-14/xplan-reactor"

    with open(lab_configuration, "r") as lab_secret:
        generate_design(experiment_id, challenge_problem, json.load(lab_secret),
                        input_dir=out_dir, out_dir=out_dir)


if __name__ == '__main__':
    main()
