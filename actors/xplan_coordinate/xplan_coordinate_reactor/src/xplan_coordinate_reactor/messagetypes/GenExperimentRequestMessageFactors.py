from ..files import split_agave_uri, make_agave_uri, upload_file_to_system
from ..jobs import launch_job
from ..logs import log_info
from .xplandesignmessage import XPlanDesignMessage
from .abacomessage import AbacoMessage, AbacoMessageError
from attrdict import AttrDict
import json
import os


class GenExperimentRequestMessageFactors(AbacoMessage):

    def process_message(self, r, timestamp, *, user_data=None):
        # the only way we should ever reach this function is
        # through the FileMessage. So expect there to be some
        # user data present.
        if user_data is None:
            raise GenExperimentRequestMessageFactorsError(
                "user_data not provided")
        if 'file' not in user_data:
            raise GenExperimentRequestMessageFactorsError(
                "file not in user_data")
        if 'file_json' not in user_data:
            raise GenExperimentRequestMessageFactorsError(
                "file_json not in user_data")
        if 'lab_configuration' not in user_data:
            raise GenExperimentRequestMessageFactorsError(
                "lab_configuration not in user_data")

        # the original 'file' from the FileMessage
        source_uri = user_data.get('file')
        (source_system, source_path) = split_agave_uri(source_uri)
        # the 'file' parsed as json
        file_json = user_data.get('file_json')
        # the lab config as established by the FileMessage
        lab_configuration = user_data.get('lab_configuration')

        # TODO this can probably be made lighter weight by using 
        # the files.manage 'copy' operation but I don't have that
        # wrapped yet and its unclear what limitations it has so
        # I am just uploading the file back to the desired location
        filename = os.path.basename(source_path)
        if filename.startswith('invocation_'):
            log_info(r, "Creating request file from invocation file")
            source_dir = os.path.dirname(source_path)
            request_file = "request_{}".format(filename[11:])
            with open(request_file, 'w') as f:
                f.write(json.dumps(file_json))
            log_info(r, "  File Name: {}".format(request_file))
            log_info(r, "  Dest System: {}".format(source_system))
            log_info(r, "  Dest Dir: {}".format(source_dir))
            upload_file_to_system(r, request_file, source_system, source_dir, verbose=True)
            log_info(r, "Uploaded request file to: {} on {}".format(source_dir, source_system))

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
