import json
import os
import numpy as np

from xplan_design.experiment_design import ExperimentDesign
from xplan_design.plate_layout import get_model_pd, solve1
from xplan_models.condition import ConditionSpace
import logging

from xplan_utils.container_data_conversion import container_to_dict, generate_container
from xplan_utils.helpers import put_experiment_request, \
    put_aliquot_properties, put_experiment_design, do_convert_ftypes
from xplan_utils.lab.strateos.utils import get_transcriptic_api, TranscripticApiError, get_tx_containers, \
    get_usable_tx_containers, generate_test_container, get_container_id

from xplan_utils import persist

l = logging.getLogger(__file__)
l.setLevel(logging.INFO)

def generate_design(request, transcriptic_cfg, out_dir='.'):
    """
    Handle experiment request based upon condition space factors
    """
    l.info("Processing GenExperimentRequestMessageFactors")
    experiment_id = request.get('experiment_id')
    base_dir = request.get('base_dir', ".")
    experiment_reference = request.get('experiment_reference')
    experiment_reference_url = request.get('experiment_reference_url')
    challenge_problem = request.get('challenge_problem')
    condition_space = ConditionSpace(factors=request.get('condition_space')['factors'])
    solver_type = request.get('solver_type', "smt")
    batches = request.get('batches')
    defaults = request.get('defaults')
    constants = defaults['constants']
    if 'strain_property' in constants:
        strain_property = constants['strain_property']
    else:
        strain_property = 'Name'
    parameters = defaults['parameters']
    conditions = defaults['conditions']
    protocol = request.get('protocol')

    submit = defaults['submit'] if 'submit' in defaults else None
    protocol_id = defaults['protocol_id'] if 'protocol_id' in defaults else None
    test_mode = defaults['test_mode'] if 'test_mode' in defaults else None

    if "exp_info.media_well_strings" in parameters:
        blank_wells = eval(parameters["exp_info.media_well_strings"])
        num_blank_wells = len(blank_wells)
    else:
        num_blank_wells = 2  # Strateos requires two blank wells
        blank_wells = []

    if base_dir == ".":
        challenge_out_dir = os.path.join(out_dir, challenge_problem)
    else:
        challenge_out_dir = os.path.join(out_dir, base_dir, challenge_problem)
    l.info("challenge_problem = " + challenge_problem)

    state = persist.get_state(challenge_out_dir)

    ## Override factor types
    for fname, factor in condition_space.factors.items():
        if fname == "timepoint" or fname == "measurement_type":
            factor['ftype'] = "shadow"

    # robj.logger.info("Generating Experiment Inputs")

    ## Save the request

    if 'experiment_requests' not in state:
        state['experiment_requests'] = []

    if experiment_id not in state['experiment_requests']:
        state['experiment_requests'].append(experiment_id)

    l.info("Stored Experiment Request: " + str(experiment_id))
    put_experiment_request(request, challenge_out_dir)

    try:
        if 'model' in state:
            raise Exception("TODO: Incorporate models into Experiment Design")
            #model = get_model(state['model'], challenge_out_dir)
        else:
            model = None

        if model is not None:
            sample_model = model['models'][0]
        else:
            sample_model = None

        try:
            transcriptic_api = get_transcriptic_api(transcriptic_cfg)
        except Exception as exc:
            l.error("Failed connecting to Transcriptic")
            raise TranscripticApiError(exc)

        if "generate" == constants['container_search_string']:
            containers = None
            usable_containers = None
        else:
            containers = get_tx_containers(transcriptic_api, constants['container_search_string'])
            if 'assigned_containers' in state:
                containers = [x for x in containers if get_container_id(x) not in state['assigned_containers']]

            # robj.logger.info("Retrieved containers: " + str(containers))
            usable_containers = get_usable_tx_containers({
                "defaults": {"source_plates": None},
                "containers": containers})
            l.info("Usable containers: %s", [get_container_id(x) for x in usable_containers])

        if solver_type == "smt":
            if 'constraints' in defaults:
                hand_coded_constraints = defaults['constraints']
            else:
                hand_coded_constraints = None
            experiment_design = generate_experiment_smt(conditions,
                                    parameters,
                                    condition_space,
                                    sample_model,
                                    constants,
                                    strain_property,
                                    blank_wells,
                                    num_blank_wells,
                                    experiment_id,
                                    experiment_reference,
                                    experiment_reference_url,
                                    protocol,
                                    state,
                                    batches,
                                    challenge_out_dir,
                                    challenge_problem,
                                    usable_containers,
                                    transcriptic_api,
                                    transcriptic_cfg,
                                    hand_coded_constraints=hand_coded_constraints,
                                    test_mode=test_mode,
                                    submit=submit)
        else:
            raise Exception("Cannot Generate Experiment with solver_type: %s", solver_type)
    except Exception as e:
        l.exception('Failed generating request')
        raise (e)

    #if submit and protocol_id is not None:
    #    l.info("Submitting Experiment: %s", experiment_id)
    #    raise Exception("TODO: Implement submission coordination")
    #    #submit_experiment(robj, experiment_id, challenge_out_dir, challenge_problem, protocol_id, test_mode)

    return experiment_design



def generate_experiment_smt(conditions,
                            parameters,
                            condition_space,
                            sample_model,
                            constants,
                            strain_property,
                            blank_wells,
                            num_blank_wells,
                            experiment_id,
                            experiment_reference,
                            experiment_reference_url,
                            protocol,
                            state,
                            batches,
                            challenge_out_dir,
                            challenge_problem,
                            usable_containers,
                            transcriptic_api,
                            transcriptic_config,
                            hand_coded_constraints=None,
                            test_mode=True,
                            submit=False):
    design, aliquot_properties = generate_experiment_request_smt(conditions,
                                                                      parameters,
                                                                      condition_space,
                                                                      usable_containers,
                                                                      batches,
                                                                      experiment_id,
                                                                      tx_config=transcriptic_config,
                                                                      strain_name=strain_property,
                                                                      hand_coded_constraints=hand_coded_constraints,
                                                                      test_mode=test_mode,
                                                                      submit=submit)

    if design is None:
        raise Exception("Could not create a design")

    if 'lab' in constants:
        design.loc[:, 'lab'] = constants['lab']

    design.loc[:, 'protocol'] = protocol

    # robj.logger.info("Design: %s", design)
    experiment_design = ExperimentDesign(experiment_id=experiment_id,
                                         parameters=parameters,
                                         design=design.to_json())

    put_experiment_design(experiment_design, challenge_out_dir)
    put_aliquot_properties(experiment_id, aliquot_properties, challenge_out_dir)

    persist.set_state(state, challenge_out_dir)

    return experiment_design






def strip_aliquot_properties(container):
    for aliquot_id in container['aliquots']:
        container['aliquots'][aliquot_id] = {}
    return container


def assign_batch_ids(design):
    containers = design.container.unique()
    design['batch'] = design.apply(lambda x: str(containers.tolist().index(x['container'])), axis=1)
    return design


def get_containers(usable_containers,
                   batches,
                   strip_aliquot_properties=False,
                   strain_name="Name"):
    if usable_containers and len(usable_containers) > 0:
        if strip_aliquot_properties:
            c2ds = {container.id: strip_aliquot_properties(container_to_dict(container, strain_name=strain_name))
                    for container in usable_containers}
        else:
            c2ds = {container.id: container_to_dict(container, strain_name=strain_name)
                    for container in usable_containers}
    else:
        c2ds = {batch['id']: generate_container(batch['samples'], batch['id'], strain_name=strain_name) for batch in
                batches}

    return c2ds


def get_plate_layout_dfs(design, volume=50):
    ## Well Index,Well Label,Vol (uL)
    container_df = design.rename(columns={"strain": "Well Label", "aliquot": "Well Index"})
    container_df['Vol (uL)'] = volume
    container_df['Well Index'] = container_df["Well Index"].apply(lambda x: x.upper())
    container_df = container_df.loc[container_df["Well Label"] != "None"]
    container_df = container_df.loc[container_df["Well Label"] != "MediaControl"]

    inducer_columns = [x for x in container_df.columns if "_concentration" in x]
    container_columns = ['Well Index', "Well Label", "Vol (uL)", 'container'] + inducer_columns

    containers = container_df[container_columns].drop_duplicates().groupby(['container'])
    return {container_id: container.drop(columns=['container']).reset_index().drop(columns=["index"])
            for container_id, container in containers}


def generate_experiment_request_smt(conditions,
                                    parameters,
                                    condition_space,
                                    usable_containers,
                                    batches,
                                    experiment_id,
                                    tx_config=None,
                                    strip_aliquot_properties=False,
                                    strain_name="Name",
                                    hand_coded_constraints=None,
                                    test_mode=True,
                                    submit=False):
    l.debug("Strain Name: %s", strain_name)
    c2ds = get_containers(usable_containers,
                          batches,
                          strip_aliquot_properties=strip_aliquot_properties,
                          strain_name=strain_name)

    factors = do_convert_ftypes(condition_space.factors)
    l.debug("factors: %s", {x: y['ftype'] for x, y in factors.items()})

    ## fix factors that have float domain and have only one value
    for factor_id, factor in factors.items():
        if factor['dtype'] == "float" and len(factor['domain']) == 1:
            factor['domain'].append(factor['domain'][0])

    inputs = {
        "samples": None,
        "factors": factors,
        "requirements": conditions,
        "containers": c2ds
    }

    model, variables = solve1(inputs, hand_coded_constraints=hand_coded_constraints)

    if model:
        l.info("Extracting dataframe for design ...")
        df = get_model_pd(model, variables, inputs['factors'])

        ## if test mode, and need to submit, then clone containers
        if test_mode and submit:
            assert (tx_config)
            containers = df.container.unique()
            for container in containers:
                l.info("Creating Test Container for container: %s", container)
                tx_container = [x for x in usable_containers if x.id == container][0]
                container_id = generate_test_container(tx_container, tx_config)
                l.info("Created Test Container: %s", container_id)
                df = df.replace(container, container_id)

        ## Drop None strain corresponding to empty wells
        df = df.loc[df.strain != "None"]

        df = assign_batch_ids(df)
        if 'sample' in df.columns:
            df['id'] = df.apply(lambda x: "_".join(str(x['sample']).split("_")[1:]),
                                axis=1)  ## drop the sample id, and just use aliquot
            # df = df.rename(columns={ "sample" : "id" })
        df['output_id'] = None
        df.loc[:, 'experiment_id'] = experiment_id

        ## Add parameters that apply to all measurements
        for parameter, value in parameters.items():
            if len(df) == 0:
                df[parameter] = [str(value)]
            else:
                df.loc[:, parameter] = str(value)

        aliquot_properties = get_plate_layout_dfs(df)

        return df, aliquot_properties
    else:
        l.info("No Model Found!")
        return None, None
