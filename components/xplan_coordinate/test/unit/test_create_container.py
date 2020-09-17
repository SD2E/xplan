import json
import logging
import os
import sys
from xplan_utils.lab.strateos.containers import generate_containers, query_protocol

transcriptic_params = {
    "default": "XPlanAutomatedExecutionTest",
    "projects": {
        "XPlanAutomatedExecutionTest": {
            "id": "p1bqm3ehqzgum",
            "nick": "Yeast Gates"
        }
    }
}


def test_create_container():
    tx_cfg_path = os.path.abspath("../../../../secrets/tx_secrets.json")
    with open(tx_cfg_path, "r") as tx_cfg_file:
        tx_cfg = json.load(tx_cfg_file)
        # query_protocol(tx_cfg, 'pr1eu2avrq8bznx')
        generate_containers([
            {
                "name": "dummy_container_01",
                "container_type": "conical-15"
            }
        ], tx_cfg, test_mode=True)


def main():
    # ensure the logger is configured
    h1 = logging.StreamHandler(sys.stdout)
    h1.setLevel(logging.DEBUG)
    h1.addFilter(lambda record: record.levelno <= logging.INFO)
    h2 = logging.StreamHandler(sys.stderr)
    h2.setLevel(logging.WARNING)
    logging.basicConfig(handlers = [h1, h2], format='%(levelname)s: %(message)s')

    test_create_container()

if __name__ == '__main__':
    main()

