import json
import logging
import os
import sys
from xplan_utils.lab.strateos.containers import make_containers

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
        # Lab Configuration
        tx_cfg = json.load(tx_cfg_file)
        # XPlanAutomatedExecutionTest project id
        tx_proj_key = transcriptic_params.get('default')
        tx_proj = transcriptic_params.get('projects').get(tx_proj_key)
        tx_proj_id = tx_proj.get('id')
        # Protocol inputs
        containers = [
            {
                "name": "dummy_container_01",
                "cont_type": "micro-1.5",
                "volume": "1000:microliter",
                "properties": [
                    {
                        "key": "concentration",
                        "value": "10:millimolar"
                    }
                ]
            }
        ]
        make_containers(tx_proj_id, tx_cfg, containers, title='TestCreateContainer', out_dir='../test_out', test_mode=True)


def main():
    # ensure the logger is configured
    h1 = logging.StreamHandler(sys.stdout)
    h1.setLevel(logging.DEBUG)
    h1.addFilter(lambda record: record.levelno <= logging.INFO)
    h2 = logging.StreamHandler(sys.stderr)
    h2.setLevel(logging.WARNING)
    logging.basicConfig(handlers=[h1, h2], format='%(levelname)s: %(message)s')

    test_create_container()


if __name__ == '__main__':
    main()
