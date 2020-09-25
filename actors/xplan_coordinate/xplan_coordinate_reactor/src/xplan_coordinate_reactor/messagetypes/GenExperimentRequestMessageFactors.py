from ..files import split_agave_uri, make_agave_uri
from ..jobs import launch_job
from ..logs import log_info
from .xplandesignmessage import XPlanDesignMessage
from .abacomessage import AbacoMessage, AbacoMessageError
from attrdict import AttrDict


class GenExperimentRequestMessageFactors(AbacoMessage):

    def process_message(self, r, timestamp, *, user_data=None):
        if user_data is None:
            raise GenExperimentRequestMessageFactorsError(
                "user_data not provided")
        # if 'file' not in user_data:
        #     raise GenExperimentRequestMessageFactorsError(
        #         "file not in user_data")
        if 'lab_configuration' not in user_data:
            raise GenExperimentRequestMessageFactorsError(
                "lab_configuration not in user_data")
        lab_configuration = user_data.get('lab_configuration')

        msg = getattr(self, 'body')
        experiment_id = msg.get('experiment_id')
        challenge_problem = msg.get('challenge_problem')

        od_settings = r.settings['xplan_config']['out_dir']
        od_system = od_settings['system']
        od_path = od_settings['path']
        out_dir = make_agave_uri(od_system, od_path)
        
        log_info(r, 
            "Processing GenExperimentRequestMessageFactors\n  Experiment ID: {}\n  Challenge Problem: {}\n OutDir: {}"
            .format(experiment_id, challenge_problem, out_dir))

        # construct an XPlanDesignMessage and run process
        message_dict = {
            "experiment_id" : experiment_id,
            "challenge_problem" : challenge_problem,
            "lab_configuration" : lab_configuration,
            "out_dir" : out_dir
        }
        log_info(r, "Constructing XPlanDesignMessage...")
        dmsg = XPlanDesignMessage(message=message_dict)
        # return dmsg.process_message(r, user_data=user_data)
        return dmsg.process_message(r, timestamp)

    def finalize_message(self, r, job, timestamp, *, user_data=None):
        raise GenExperimentRequestMessageFactorsError(
            "finalize_message should not be called for GenExperimentRequestMessageFactors")

class GenExperimentRequestMessageFactorsError(AbacoMessageError):
    pass
