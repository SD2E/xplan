import json

from xplan_design.design import generate_design
import argparse

def _parser():
    parser = argparse.ArgumentParser(description='XPlan Generate Design')
    parser.add_argument('invocation', help='Design Inocation Data')
    parser.add_argument('lab_configuration', help='Lab LIMS credentials')
    parser.add_argument("out_dir", help="Base directory for output", default=".")
    return parser

def main():
    parser = _parser()
    args = parser.parse_args()

    invocation = args.invocation
    lab_configuration = args.lab_configuration
    out_dir = args.out_dir
    #out_dir = "/work/projects/SD2E-Community/prod/projects/sd2e-project-14/xplan-reactor"

    with open(invocation, "r") as experiment_request, open(lab_configuration, "r") as lab_secret:
        generate_design(json.load(experiment_request), json.load(lab_secret), out_dir)

if __name__ == '__main__':
    main()
