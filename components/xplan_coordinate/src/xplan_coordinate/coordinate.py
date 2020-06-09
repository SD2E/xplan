import logging

from xplan_design.design import generate_design
from xplan_submit.lab.strateos.submit import submit_experiment
from xplan_submit.lab.strateos.write_parameters import design_to_parameters

l = logging.getLogger(__file__)
l.setLevel(logging.INFO)


def coordinate_submission(request, xplan_config, transcriptic_cfg, transcriptic_params, out_dir='.', mock=True):
    """
    Design an experiment, write the parameters, and submit it.
    :param request:
    :param xplan_config:
    :param transcriptic_cfg:
    :param out_dir:
    :return:
    """
    design = generate_design(request, xplan_config, transcriptic_cfg, out_dir=out_dir)
    parameters = design_to_parameters(request,
                         design,
                         transcriptic_cfg,
                         out_dir = out_dir)
    completed_design = submit_experiment(request, design, xplan_config, transcriptic_cfg, transcriptic_params, parameters=parameters,
                      out_dir=out_dir, mock=mock)
    return completed_design