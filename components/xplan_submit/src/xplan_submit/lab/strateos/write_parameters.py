import json
import os
import random
from random import sample, uniform

from functools import reduce
import operator
import pandas as pd
import numpy as np

import logging

from transcriptic.jupyter import objects
from xplan_design.experiment_design import ExperimentDesign
from xplan_models.condition import ConditionSpace
from xplan_utils.helpers import NpEncoder, put_tx_parameters, do_convert_ftypes, get_experiment_design, \
    get_experiment_request
from xplan_utils.lab.strateos.utils import get_tx_containers, get_transcriptic_api, TranscripticApiError, get_container_id

l = logging.getLogger(__file__)
l.setLevel(logging.INFO)

def design_to_parameters(experiment_id,
                         transcriptic_cfg,
                         input_dir=".",
                         out_dir="."):
    experiment_design = get_experiment_design(experiment_id, input_dir)
    experiment_request = get_experiment_request(experiment_id, input_dir)

    design = pd.read_json(experiment_design['design'])

    batches = experiment_request.get("batches")
    parameters = experiment_request['defaults']['parameters']
    condition_space = ConditionSpace(factors=experiment_request.get('condition_space')['factors'])
    experiment_id = experiment_design['experiment_id']
    experiment_reference = experiment_request["experiment_reference"]
    experiment_reference_url = experiment_request['experiment_reference_url']
    if 'strain_property' in experiment_request['defaults']['constants']:
        strain_property = experiment_request['defaults']['constants']['strain_property']
    else:
        strain_property = 'Name'
    if "exp_info.media_well_strings" in parameters:
        blank_wells = eval(parameters["exp_info.media_well_strings"])
        num_blank_wells = len(blank_wells)
    else:
        num_blank_wells = 2  # Strateos requires two blank wells
        blank_wells = []
    try:
        transcriptic_api = get_transcriptic_api(transcriptic_cfg)
    except Exception as exc:
        l.error("Failed connecting to Transcriptic")
        raise TranscripticApiError(exc)

    base_dir = experiment_request.get('base_dir', ".")
    challenge_problem = experiment_request.get('challenge_problem')
    if base_dir == ".":
        challenge_out_dir = os.path.join(out_dir, challenge_problem)
    else:
        challenge_out_dir = os.path.join(out_dir, base_dir, challenge_problem)

    params = {}
    for batch in batches:
        param, design, container = get_invocation_parameters(batch,
                                                             parameters,
                                                             condition_space,
                                                             design,
                                                             transcriptic_api,
                                                             experiment_id,
                                                             experiment_reference,
                                                             experiment_reference_url,
                                                             strain_property=strain_property,
                                                             blank_wells=blank_wells,
                                                             num_blank_wells=num_blank_wells,
                                                             convert_ftypes=True)
        if param is not None:
            put_tx_parameters(experiment_id,
                              str(batch['id']),
                              json.dumps(param, indent=4, sort_keys=True, separators=(',', ': '), cls=NpEncoder),
                              challenge_out_dir)
            params[batch['id']] = param
    return params



def get_invocation_parameters(batch,
                              parameters,
                              condition_space,
                              design,
                              transcriptic_api,
                              experiment_id,
                              experiment_reference,
                              experiment_reference_url,
                              strain_property="Name",
                              blank_wells=[], num_blank_wells=2,
                              convert_ftypes=False):
    """
    Express samples in invocaction paramter format.
    """
    l.debug("get_invocation_parameters for design: %s", str(design))

    batch_samples = design.loc[design['batch'].astype(str) == str(batch['id'])]

    l.debug("Batch samples to parameters: " + str(batch_samples))

    if len(batch_samples) == 0:
        return None, design, None

    ## Get the protocol type to decide how to map design to lab parameters
    protocol = batch_samples.protocol.unique()[0]
    l.debug("Batch uses protocol: %s", str(protocol))
    if protocol == 'timeseries' or protocol == 'obstacle_course' or protocol == 'growth_curve':
        return get_time_series_invocation_parameters(batch_samples, batch, parameters, condition_space, design,
                                                     transcriptic_api, experiment_id, experiment_reference,
                                                     experiment_reference_url, strain_property=strain_property,
                                                     blank_wells=blank_wells, num_blank_wells=num_blank_wells,
                                                     convert_ftypes=convert_ftypes)
    elif protocol == 'pr1dbghhavd9ykm':
        return get_harmonized_invocation_parameters(batch_samples, batch, parameters, condition_space, design,
                                                    transcriptic_api)
    else:
        raise Exception("Unknown protocol %s", protocol)


class AutoVivification(dict):
    """Implementation of perl's autovivification feature."""

    def __getitem__(self, item):
        try:
            return dict.__getitem__(self, item)
        except KeyError:
            value = self[item] = type(self)()
            return value


def getFromDict(dataDict, mapList):
    return reduce(operator.getitem, mapList, dataDict)


def setInDict(dataDict, mapList, value):
    getFromDict(dataDict, mapList[:-1])[mapList[-1]] = value


def make_entry(av_dict, key, value):
    """
    Helper function to make turn dot-ified key string into a list of keys
    corresponding to nested dicts and assign value to resulting nesting.  If
    path indicated by keys does not exist, then create it.
    """
    key_list = key.split('.')
    setInDict(av_dict, key_list, value)


def get_matching_aliquots(strains, container_id, merge_key="Name", blank_wells=[], num_blank_wells=2):
    """
    Determine which aliquots in container match a strain in strains.
    strains may or may not include blanks and media controls.  Similarly,
    the aliquots may or may not include blanks and media controls.  If the
    aliquots do not have blanks or media controls, but have space for them,
    then assume the empty spaces can be blanks or media controls.  If the strains
    have blanks, then let them be either blanks or media controls.
    """

    c = objects.Container(container_id)

    aliquots = c.aliquots

    ## Extend aliquots with blanks if not all aliquots specified.
    if len(aliquots) < c.container_type.well_count:
        for i in range(0, c.container_type.well_count):
            if i not in aliquots.index:
                row = {x: None for x in aliquots.columns}
                row[merge_key] = ""
                aliquots.loc[i] = row

    ## Replace strains that are None with ""
    aliquots = aliquots.replace(to_replace=[None], value="")

    ## aliquots[merge_key] = aliquots[merge_key].replace([None], "")
    ## aliquots[merge_key] = aliquots[merge_key].replace(["MediaControl"], "")
    ## if len(aliquots) < c.container_type.well_count and "" in strains:
    ##     for i in range(0, c.container_type.well_count):
    ##         if i not in aliquots.index and i not in blank_wells:
    ##             row = { x : None for x in aliquots.columns}
    ##             row[merge_key] = ""
    ##             aliquots.loc[i] = row

    ## Determine which strains are present in aliquots
    strain_df = pd.DataFrame({merge_key: strains})
    aliquots['index'] = c.aliquots.index
    matches = aliquots.merge(strain_df, on=merge_key, how="inner")
    l.debug("Matched: %s\n", str(matches.groupby([merge_key]).agg(len)))

    ##Assume that any unmatched blanks or media controls are matched with blanks
    mismatches = [x for x in strains if x not in matches[merge_key].unique()]
    l.debug("Didn't Match: %s\n", str(mismatches))

    def is_matchable(mismatch):
        return "MediaControl" == mismatch or \
               mismatch is None or \
               np.isnan(mismatch)

    matchable_mistmatches = [x for x in mismatches if is_matchable(x)]

    if len(matchable_mistmatches) > 0:
        strain_df = pd.DataFrame({merge_key: [""]})
        match_mismatches = aliquots.merge(strain_df, on=merge_key, how="inner")
        l.debug("match_mismatches: %s", match_mismatches)
        matches = matches.append(match_mismatches)

    matches = matches.set_index('index')
    l.debug("final matches: %s", matches)

    return matches


def get_src_wells_from_aliquots(container_id, matching_aliquots):
    return [{"containerId": container_id, "wellIndex": x} for x in matching_aliquots.index.tolist()]


def get_matching_container(strains, transcriptic_api, strain_property="Name", container_search_string="",
                           blank_wells=[], num_blank_wells=2):
    results = get_tx_containers(transcriptic_api, container_search_string)
    l.debug("Got %d results for container", len(results))
    for result in results:
        container_id = get_container_id(result)
        l.debug("Checking container_id for match: %s", container_id)
        matching_aliquots = get_matching_aliquots(strains, container_id, merge_key=strain_property,
                                                  blank_wells=blank_wells, num_blank_wells=num_blank_wells)
        l.debug("Matching aliquots: %s", str(matching_aliquots))
        if matching_aliquots is not None:
            return container_id, matching_aliquots

    raise Exception("Could not find container with strains: %s", strains)


def add_reagent_concentrations(invocation_params, batch_samples, reagents, parameters):
    if len(reagents) == 0:
        make_entry(invocation_params, "induction_info.induction_reagents.inducer_layout", {
            "value": "select_cols",
            "inputs": {
                "select_cols": {
                    "col_and_conc": [
                        {"col_num": x, "conc": 0.0}
                        for x in range(1, 13)
                    ]
                }
            }
        })
    else:

        col_conc = []
        for reagent in reagents:
            col_conc_df = batch_samples[[reagent, 'column_id']].drop_duplicates().rename(
                columns={"column_id": "col_num", reagent: "conc"}).dropna().replace("NA", 0.0)

            values = col_conc_df.conc.astype(float).unique()
            if len(values) == 1 and 0.0 in values:
                continue ## Ignore zero inducers

            ## If there are multiple reagents in the ER, then need to select the right one for this plate
            reagent_name = reagent.split("_concentration")[0]
            if 'inducers' in parameters:
                for k, v in parameters['inducers'][reagent_name].items():
                    make_entry(invocation_params, k, v)

            col_conc = col_conc_df.astype({"conc": "float", "col_num": "int32"}).to_dict('records')
            cols_used = [x['col_num'] for x in col_conc]
            for col in range(1, 13):
                if not col in cols_used:
                    col_conc.append({"col_num": col, "conc": 0.0})

            #    col_conc.append(col_conc_df.astype({ "col_num" : "int32"}).to_dict('records'))

        ## inducer_container = {
        ##     "containerId" : "ct1ar3npr7fg2x",
        ##     "wellIndex" : 0
        ##     }
        ## make_entry(invocation_params, "induction_info.induction_reagents.inducer", inducer_container)
        make_entry(invocation_params, "induction_info.induction_reagents.inducer_layout.value", "select_cols")
        make_entry(invocation_params,
                   "induction_info.induction_reagents.inducer_layout.inputs.select_cols.col_and_conc", col_conc)
    return invocation_params


def input_state_for_epoch(samples, epoch):
    def get_inputs(row):
        input_str = ""
        index = 0
        cols = list(row.index)
        cols.sort()

        for col in cols:
            if type(row[col]) is str and row[col] == "NA":
                return "NA"  ## If any of the inputs is an NA, then no inputs for epoch
            elif float(row[col]) != 0.0:
                if index == 0:
                    input_str += "a"
                else:
                    input_str += "b"
            index += 1
        if input_str == "":
            input_str = "off"
        return input_str

    inputs_for_epoch = [x for x in samples.columns if "@ {}".format(epoch) in x]
    inputs_for_epoch.sort()
    l.debug("samples: %s", samples)
    l.debug("inputs_for_epoch %s", inputs_for_epoch)
    input_state = samples[inputs_for_epoch].drop_duplicates().apply(get_inputs, axis=1)
    l.debug("input_state = %s", input_state)
    return input_state.iloc[0]


def num(s):
    try:
        return int(s)
    except ValueError:
        return int(float(s))


def get_inducer_and_time(term):
    at_split = term.split("@")
    inducer = at_split[0]
    space_split = at_split[1].strip().split(" ")
    time = num(space_split[0])
    return inducer, time


def get_obstacle_course_conditions(batch_samples):
    inputs_and_epochs = [get_inducer_and_time(x) for x in batch_samples.columns if "@" in x]
    if len(inputs_and_epochs) > 0:
        epochs = list(set([x for _, x in inputs_and_epochs]))
        epochs.sort()
        inputs = list(set([x for x, _ in inputs_and_epochs]))
        inputs.sort()

        columns = batch_samples.column_id.dropna().unique()
        columns.sort()

        input_states = [[input_state_for_epoch(batch_samples.loc[batch_samples.column_id == column], epoch)
                         for i, epoch in enumerate(epochs)]
                        for column in columns]

        max_epochs = max([len([x for x in input_states[i] if x != "NA"]) for i, column in enumerate(columns)])

        result = {
            "inputs": {
                str(max_epochs): {
                    "condition": [
                        {
                            ##Assumes one epoch per day
                            "day_{}".format(i + 1): input_state
                            for i, input_state in enumerate(input_states[c]) if input_state != "NA"
                            #                            "day_{}".format(i+1) : input_state_for_epoch(batch_samples.loc[batch_samples.column_id == column],
                            #                                                                       epoch)
                            #                            for i, epoch in enumerate(epochs)

                        }
                        for c, column in enumerate(columns)
                    ]
                }
            },
            "value": str(max_epochs)
        }
    else:
        result = {
            "inputs": {
                "1": {
                    "condition": [
                        {
                            "day_1": "off"
                        }
                        for i in range(0, 12)
                    ]
                }
            },
            "value": "1"
        }
    return result


def get_obstacle_course_dilution_volume(batch_samples, culture_volume):
    dilution_factor = int(batch_samples["Dilution factor"].dropna().drop_duplicates().values[0])
    return culture_volume * (dilution_factor - 1)


def get_container_for_batch(batch, batch_samples, design, condition_space,
                            transcriptic_api, convert_ftypes=False,
                            blank_wells=[],
                            strain_property="Name",
                            num_blank_wells=2):
    ## Get the source_container
    if 'container' in batch_samples.columns and len(batch_samples.container.dropna()) > 0:
        ## Already know the container id, so just get the container object
        container_id = batch_samples.container.unique()[0]
        try:
            containers = get_tx_containers(transcriptic_api, [container_id])
        except Exception as e:
            containers = None

        if containers:
            ## Have containers at lab already
            possible_containers = [x for x in containers if get_container_id(x) == container_id]
            if len(possible_containers) > 0:
                source_container = possible_containers[0]
            else:
                ## Try to retreive container from tx
                source_container = get_tx_containers(transcriptic_api, [container_id])[0]
        else:
            ## Need to make a container at the lab
            ## FIXME create a container and upload here
            source_container = None
            raise Exception("Need to handle case where we need to create a container")
    else:
        raise Exception("No container assigned for batch in design")
    ## FIXME need to add the wells to the strain inputs
    l.debug("source_container = %s", str(source_container))

    ## This function will find a container that has the strains we need, but the way its
    ## used here, we already know the container we want to use.  We overload the search
    ## so that it finds the container we wanted.
    ## The matching_aliquots are a dataframe that has the aliquot properties of wells in
    ## the container that correspond to the strains in first argument below.
    if not 'aliquot' in batch_samples:
        container_id, matching_aliquots = get_matching_container(batch_samples.strain.unique(),
                                                                 transcriptic_api,
                                                                 strain_property=strain_property,
                                                                 container_search_string=get_container_id(
                                                                     source_container),
                                                                 blank_wells=blank_wells,
                                                                 num_blank_wells=num_blank_wells)
    else:
        matching_aliquots = None

    if matching_aliquots:
        ## The samples are used in protocol parameters to indicate which wells to measure
        samples = get_src_wells_from_aliquots(container_id, matching_aliquots)
        matching_aliquots['used'] = False
    else:
        samples = [{"containerId": container_id, "wellIndex": source_container.container_type.robotize(x)}
                   for x in batch_samples[batch_samples.strain != "MediaControl"].aliquot.unique()]

    ## This function will pick an aliquot in matching_samples to use for a sample
    def assign_output_id(x):
        if x['batch'] == batch['id']:
            l.debug("Assigning aliquot for: %s", x)
            if pd.isnull(x.strain):
                open_aliquots = matching_aliquots.loc[
                    (matching_aliquots[strain_property].isna()) & (~matching_aliquots['used'])].index
                l.debug("matching_aliquots: %s", matching_aliquots.loc[(matching_aliquots[strain_property].isna())])
            elif x.strain == "MediaControl":
                open_aliquots = matching_aliquots.loc[
                    (matching_aliquots[strain_property] == "") & (~matching_aliquots['used'])].index
                l.debug("matching_aliquots: %s",
                        matching_aliquots.loc[(matching_aliquots[strain_property] == x.strain)])
            else:
                open_aliquots = matching_aliquots.loc[
                    (matching_aliquots[strain_property] == x.strain) & (~matching_aliquots['used'])].index
                l.debug("matching_aliquots: %s",
                        matching_aliquots.loc[(matching_aliquots[strain_property] == x.strain)])
            l.debug("open_aliquots = %s", open_aliquots)
            aliquot = open_aliquots[0]
            matching_aliquots.loc[aliquot, 'used'] = True
            return aliquot
        elif 'output_id' in x:
            return x['output_id']
        else:
            return None

    ## The following code decides what columns of the design to project onto to indentify aliquot specific properties
    l.debug("convert_ftypes: %s", convert_ftypes)
    if convert_ftypes:
        shadow_factors = [name for name, factor in do_convert_ftypes(condition_space.factors).items()
                          if factor['ftype'] == 'sample']
        shadow_factors.append('sample')  # id will be different for each sample
    else:
        shadow_factors = [name for name, factor in condition_space.factors.items()
                          if factor['ftype'] == 'shadow']
    shadowed_cols = design[shadow_factors].drop_duplicates()
    non_shadow_design = design.drop(columns=shadow_factors).drop_duplicates()

    l.debug("Design projected onto measurements: %s", non_shadow_design)

    ## Map the output_id if needed
    if not "aliquot" in non_shadow_design and matching_aliquots is not None:
        non_shadow_design['output_id'] = non_shadow_design.apply(assign_output_id, axis=1)
    else:
        non_shadow_design['output_id'] = non_shadow_design['aliquot']

    ## Track the container_id in the design if not already present
    def assign_container_id(x):
        if x['batch'] == batch['id']:
            return container_id
        elif 'container' in x:
            return x['container']
        else:
            return None

    if 'container' not in non_shadow_design:
        non_shadow_design['container'] = non_shadow_design.apply(assign_container_id, axis=1)

    ## Get the output_id and container from the projected design and merge back into overall design
    fdf = non_shadow_design[['id', 'output_id', 'container']]

    if 'container' in design.columns:
        design = design.drop(columns=['container'])
    design = design.drop(columns=['output_id']).merge(fdf, how='left', on='id')

    return design, source_container, samples


def repair_parameter_value(k, v):
    if k == "exp_info.media_well_strings":
        return v.replace(" ", "")
    else:
        return v


def get_time_series_invocation_parameters(batch_samples,
                                          batch,
                                          parameters,
                                          condition_space,
                                          design,
                                          transcriptic_api,
                                          experiment_id,
                                          experiment_reference,
                                          experiment_reference_url,
                                          strain_property="Name",
                                          blank_wells=[],
                                          num_blank_wells=2,
                                          convert_ftypes=False):
    l.info("Creating Timeseries invocation parameters...")
    protocol = batch_samples.protocol.unique()[0]
    invocation_params = AutoVivification()
    exp_params = parameters.copy()

    omit_parameters = ["inducers"]

    for k, v in exp_params.items():
        l.debug("Setting %s = %s", str(k), str(v))
        v1 = repair_parameter_value(k, v)
        if k in omit_parameters:
            continue
        make_entry(invocation_params, k, v1)

    for fname, factor in condition_space.factors.items():
        if 'lab_name' in factor and (factor['ftype'] == 'batch' or factor['ftype'] == 'experiment'):
            k, v = factor_to_param(fname, factor, batch_samples, protocol)
            if type(k) is not list:
                k = [k]
            for kk in k:
                make_entry(invocation_params, kk, v)

    design, source_container, samples = get_container_for_batch(batch, batch_samples, design,
                                                                condition_space,
                                                                transcriptic_api,
                                                                strain_property=strain_property,
                                                                convert_ftypes=convert_ftypes,
                                                                blank_wells=blank_wells,
                                                                num_blank_wells=num_blank_wells)

    if protocol == 'growth_curve':
        timepoint_str = extract_timepoints(batch_samples)
        make_entry(invocation_params, 'read_info.growth_time.sample_points', timepoint_str)
        make_entry(invocation_params, 'src_info.src_samples', samples)
    elif protocol == 'timeseries':
        ## Add reagent column concentrations
        reagents = [factor_id for factor_id, factor in condition_space.factors.items() if factor['ftype'] == 'column']
        invocation_params = add_reagent_concentrations(invocation_params, batch_samples, reagents, parameters)
        make_entry(invocation_params, 'exp_info.src_samples', samples)

        timepoint_str = extract_timepoints(batch_samples)
        make_entry(invocation_params, 'induction_info.induction_time.sample_points', timepoint_str)


        ## Set recovery media to media used in induction and inoculation
        ## FIXME need to set media as part of factor
        if "recovery_info" in invocation_params and len(invocation_params['recovery_info']) > 0:
            media = invocation_params['inoc_info']['inoculation_media']
            for recovery in invocation_params['recovery_info']:
                recovery['recovery_media'] = media

    elif protocol == 'obstacle_course':
        make_entry(invocation_params, 'exp_info.src_plate', get_container_id(source_container))
        conditions = get_obstacle_course_conditions(batch_samples)
        make_entry(invocation_params, 'reagent_info.inducer_info.inputs.2.conditions', conditions)
        culture_volume_str = str(invocation_params['exp_info']['growth_volumes']['culture_volume'])
        culture_volume = culture_volume_str.split(":")[0]
        culture_volume_units = culture_volume_str.split(":")[1]
        dilution_volume = int(get_obstacle_course_dilution_volume(batch_samples, int(culture_volume)))
        make_entry(invocation_params, 'exp_info.growth_volumes.media_volume',
                   "{}:{}".format(dilution_volume, culture_volume_units))

    make_entry(invocation_params, 'experimental_info.experiment_id', experiment_id)
    make_entry(invocation_params, 'experimental_info.experiment_reference', experiment_reference)
    make_entry(invocation_params, 'experimental_info.experiment_reference_url', experiment_reference_url)

    final_invocation_params = {"parameters": invocation_params}
    l.debug("after batch params, design: %s", str(design))
    return final_invocation_params, design, source_container

def extract_timepoints(batch_samples):
    timepoints = list(batch_samples.timepoint.unique())
    if 0.0 in timepoints:
        timepoints.remove(0.0)  ## Timepoint 0 will be read automatically, do not need to specify
    if len(timepoints)  == 1:
        timepoint_str = str([timepoints[0]])
    else:
        timepoint_str = ','.join(map(str, map(int, timepoints)))
    return timepoint_str

def factor_to_param(factor_name, factor, batch_samples, protocol, logger=l):
    if factor_name not in batch_samples.columns:
        raise Exception("Experiment Design is missing factor: " + factor_name)
    if len(batch_samples[factor_name].dropna()) == 0:
        raise Exception("Experiment Design does not assign values to factor: " + factor_name)

    value = batch_samples[factor_name].unique()[0]
    logger.debug("Converting factor " + str(factor) + " to parameter")

    ## FIXME use DD
    mapped_values = {
        "M9 Glucose CAA (a.k.a. M9 Glucose Stock)": "M9 Minimal Media",
        "Modified M9 Media": "modified_m9_media",
        "Modified M9 Media + Kan 5_ug_per_ml": "modified_m9_media_with_kan_5ug_per_ml"
    }
    time_series_mapped_values = {
        "M9 Glucose CAA (a.k.a. M9 Glucose Stock)": "M9 Minimal Media"
    }
    if value in mapped_values and protocol != "timeseries":
        value = mapped_values[value]
    elif value in time_series_mapped_values and protocol == "timeseries":
        value = time_series_mapped_values[value]

    if 'lab_suffix' in factor:
        value = str(int(value)) + factor['lab_suffix']
    if 'lab_prefix' in factor:
        value = factor['lab_prefix'] + str(int(value))
    if type(value) is str and value == "true":
        value = True
    if type(value) is str and value == "false":
        value = False

    return factor['lab_name'], value

def get_dest_well(dest_wells):
    """
    Sample one well
    """

    well = sample(dest_wells, 1)
    dest_wells.remove(well[0])
    return well[0]

def get_harmonized_invocation_parameters(batch_samples, batch, parameters, condition_space, design, transcriptic_api,
                                         containers, logger=l):
    exp_params = parameters.copy()

    # growth_media_2, inc_time_2, inc_temp,
    for factor_name, factor in condition_space.factors.items():
        if factor_name not in batch_samples.columns:
            raise Exception("Experiment Design is missing factor: " + factor_name)
        if len(batch_samples[factor_name].dropna()) == 0:
            raise Exception("Experiment Design does not assign values to factor: " + factor_name)

        if 'lab_name' in factor:
            logger.debug("Converting factor " + str(factor) + " to parameter")
            value = batch_samples[factor_name].unique()[0]
            if 'lab_suffix' in factor:
                value = str(int(value)) + factor['lab_suffix']
            if 'lab_prefix' in factor:
                value = factor['lab_prefix'] + str(int(value))
            exp_params[factor['lab_name']] = value

    batch_protocol = design['protocol'].unique()[0]

    source_container = random.choice(containers)
    exp_params['source_plate'] = source_container['id']
    container = objects.Container(source_container['id'])
    aliquots = container.aliquots
    dest_wells = [x + str(y) for x in ["A", "B", "C", "D", "E", "F", "G", "H"] for y in range(1, 12)]

    samples = []

    strain_groups = batch_samples.groupby(['strain'])
    for strain, group in strain_groups:
        dests = []
        for i, sample in group.iterrows():
            od = sample.od
            dest_well = get_dest_well(dest_wells)
            design.loc[i, 'output_id'] = dest_well
            dests.append({"dest_well": dest_well, "targ_od": od})
        logger.debug("Adding transfers for " + str(strain))
        source = get_source_for_strain(aliquots, strain)

        src_well = container.container_type.humanize(source['index'])
        samples.append({"source_well": src_well, "dest_od": dests})

    #    for row, sample in batch_samples.iterrows():
    #        samples.append(get_sample_from_row(sample))

    specify_locations = {}
    specify_locations['samples'] = samples
    inputs = {}
    inputs['specify_locations'] = specify_locations
    sample_selection = {}
    sample_selection['inputs'] = inputs
    sample_selection['value'] = "specify_locations"

    parameters = {}
    parameters['exp_params'] = exp_params
    parameters['sample_selection'] = sample_selection
    invocation_params = {}
    invocation_params['parameters'] = parameters

    return invocation_params, design, source_container


def add_timepoints(design, condition_space, conditions):
    """
    FIXME, adds all timepoints in factor domain to the design for each sample.
    """
    if 'timepoint' in condition_space.factors:
        timerange = condition_space.factors['timepoint']['domain']
        timepoints = list(range(timerange[0], timerange[1]))
        design.loc[:, 'key'] = 0
        design = design.drop(columns=['timepoint'])
        fdf = pd.DataFrame({'timepoint': timepoints})
        # l.info(fdf)
        fdf.loc[:, 'key'] = 0
        design = design.merge(fdf, how='left', on='key').drop(columns=['key'])
        l.debug(design)

        def add_timepoint_to_id(x):
            return x['id'] + "_" + str(x['timepoint'])

        # design.loc[:,'id'] = design.apply(add_timepoint_to_id, axis=1)

    return design

def get_source_for_strain(aliquots, strain):
    for i in aliquots.index:
        if aliquot_matches(aliquots[i:i+1], strain):
            alq = aliquots[i:i+1].to_dict()
            alq['Volume'] = str(alq['Volume']) # Volume is Unit class
            alq['index'] = i
            return alq
    raise Exception("Could not find aliquot for strain: " + str(strain))

def aliquot_matches(aliquot, strain):
    return strain == str(aliquot.iloc[0]['SynBioHub URI'])
