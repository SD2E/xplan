import logging

from xplan_design.design import generate_design
from xplan_submit.lab.strateos.submit import submit_experiment
from xplan_submit.lab.strateos.write_parameters import design_to_parameters

l = logging.getLogger(__file__)
l.setLevel(logging.INFO)


def coordinate_submission(experiment_id, transcriptic_cfg, transcriptic_params, input_dir='.', out_dir='.', mock=True):
    """
    Design an experiment, write the parameters, and submit it.
    :param request:
    :param transcriptic_cfg:
    :param out_dir:
    :return:
    """
    generate_design(experiment_id, transcriptic_cfg, input_dir=input_dir, out_dir=out_dir)
    design_to_parameters(experiment_id,
                         transcriptic_cfg,
                         input_dir=out_dir,
                         out_dir = out_dir)
    submit_experiment(experiment_id, transcriptic_cfg, transcriptic_params, input_dir=out_dir, out_dir=out_dir,
                      mock=mock)
