import pandas as pd
import logging
import numpy as np

#from synbiohub_adapter.query_synbiohub import *
#from synbiohub_adapter.SynBioHubUtil import *
#from sbol import *

l = logging.getLogger(__file__)
l.setLevel(logging.INFO)

def containers_have_known_contents(containers, factors, aliquot_factor_map):
    for container_id, c in containers.items():
        for aliquot, aliquot_properties in c['aliquots'].items():
            for factor, level in aliquot_properties.items():
                if factors[factor]['dtype'] == "str":
                    if level not in aliquot_factor_map[factor] or aliquot_factor_map[factor][level] not in factors[factor]['domain']:
                        l.exception(f"{level} from {container_id} {aliquot} is not part of the condition space for factor {factor}")
                        return False
                else:
                    if level not in aliquot_factor_map[factor] or aliquot_factor_map[factor][level] < factors[factor]['domain'][0] or aliquot_factor_map[factor][level] > factors[factor]['domain'][1]:
                        l.exception(f"{level} from {container_id} {aliquot} is not part of the condition space for factor {factor}")
                        return False
    return True


def get_aliquot_row(aliquot, container):
    for row in container['rows']:
        if aliquot in container['rows'][row]:
            return row
    return None

def get_aliquot_col(aliquot, container):
    for col in container['columns']:
        if aliquot in container['columns'][col]:
            return col
    return None

def get_column_id(column):
    """
    Convert colX to X
    """
    return int(column.split("col")[1])

def get_column_name(col, container_id):
    return "{}_{}".format(col, container_id)


def get_column_factors(column_factors, col, container_id):
    col_name = get_column_name(col, container_id)
    l.debug("column_factors: %s, %s", col, column_factors[col_name])
    return column_factors[col_name]

def get_row_id(row):
    """
    Convert rowX to X
    """
    return int(row.split("row")[1])

def get_row_name(row, container_id):
    return "{}_{}".format(row, container_id)


def get_row_factors(row_factors, row, container_id):
    row_name = get_row_name(row, container_id)
    l.debug("row_factors: %s, %s", row, row_factors[row_name])
    return row_factors[row_name]


def get_samples_from_condition_set(factors, condition_set, parameters = None, use_tbd=False):
    """
    Compute factorial experiment from condition_set and parameters.
    """
    l.debug(factors)
    l.debug(condition_set)
    if not condition_set_is_singletons(factors, condition_set):
        samples = condition_set_cross_product(factors, condition_set)
    else:
        samples = pd.DataFrame({ factor['factor'] : factor['values'] for factor in condition_set['factors'] if factor['factor'] in factors})

    l.debug(samples)

#    if len(samples) == 0:
#        # There are no elements of condition_set that refer to factors
#        return samples
    
    if 'key' in samples.columns:
        samples = samples.drop(columns=['key'])

    if parameters:
        for parameter, value in parameters.items():
            if len(samples) == 0:
                samples[parameter] = [str(value)]
            else:
                samples.loc[:, parameter] = str(value)

    if use_tbd:
        if len(samples) == 0:
            samples = pd.DataFrame({ factor : ["TBD"] for factor in factors})
        else:
            # Add columns for factors not present in the condition_set
            for factor in factors:
                if factor not in samples.columns:
                    l.debug("adding %s", factor)
                    samples.loc[:, factor] = "TBD"
    else:
        for factor in factors:
            if factor not in samples.columns:
                l.debug("adding %s", factor)
                if len(samples) > 0:
                    samples.loc[:, factor] = np.nan
    
    return samples

def get_factor_from_condition_set(factor_id, condition_set):
    for cs_factor in condition_set['factors']:
        if cs_factor['factor'] == factor_id:
            return cs_factor
    return None
    #raise Exception("Could not find factor %s in condition_set %s", factor_id, condition_set)

def condition_set_is_singletons(factors, condition_set):
    for constraint in condition_set['factors']:
        if len(constraint['values']) > 1:
            return False
    return True

def condition_set_cross_product(factors, condition_set):
    samples = pd.DataFrame()
    for factor_id in factors:
        factor = get_factor_from_condition_set(factor_id, condition_set)
        #if factors[factor['factor']]['ftype'] == 'time':
        #    continue

#        if "" in factor['values']:
#            factor['values'].remove("")
        if factor is None:
            continue
        if len(factor['values']) == 0:
            l.debug("Skipping factor %s, no values", factor['factor'])
            continue
        
        l.debug("Merging factor %s = %s", factor['factor'], factor['values'])

        
        if len(samples) == 0:
            samples = pd.DataFrame({factor['factor'] : factor['values']})
        else:
            samples.loc[:,'key'] = 0
            fdf = pd.DataFrame({factor['factor'] : factor['values']})
            #l.info(fdf)
            fdf.loc[:,'key'] = 0
            samples = samples.merge(fdf, how='left', on='key')
    return samples



def resolve_common_term(common_term, user, password):
    # SBH requiress authentication
    sbh_query = SynBioHubQuery(SD2Constants.SD2_SERVER)
    sbh_query.login(user, password)
    # Option 1: Look up a dictionary value, by lab id -> provide Common Name and URI as output
    common_term = 'B_subtilis_LG227_Colony_1'
    designs = sbh_query.query_designs_by_lab_ids(SD2Constants.TRANSCRIPTIC, common_term, verbose=True)
    sbh_uri = designs[common_term]['identity']
    mapped_name = designs[common_term]['name']
    # https://hub.sd2e.org/user/sd2e/design/B_subtilis_LG227/1
    #print(sbh_uri)
    # B_subtilis_LG227
    #print(mapped_name)
    return sbh_uri

def resolve_sbh_uri(sbh_uri, user, password):
    # SBH requiress authentication
    sbh_query = SynBioHubQuery(SD2Constants.SD2_SERVER)
    sbh_query.login(user, password)

    # Option 2: Look up a dictionary value by URI -> provide lab id and Common Name as output
    value_to_query = 'https://hub.sd2e.org/user/sd2e/design/B_subtilis_LG227/1'
    lab_ids = sbh_query.query_lab_ids_by_designs(SD2Constants.TRANSCRIPTIC, value_to_query, verbose=True)
    # [{'id': 'B_subtilis_LG227_Colony_1', 'name': 'B_subtilis_LG227'}, {'id': 'B_subtilis_LG227_Colony_2', 'name': 'B_subtilis_LG227'}, {'id': 'B_subtilis_LG227_Colony_3', 'name': 'B_subtilis_LG227'}]
    return lab_ids[sbh_uri]

def container_dict_to_df(container_dict, aliquot_factor_map):
    df = pd.DataFrame.from_dict(container_dict['aliquots'], orient='index').reset_index()
    df = df.rename(columns={"index" : "aliquot"})
    for factor in aliquot_factor_map:
        if factor in df.columns:
            df[factor] = df[factor].apply(lambda x: aliquot_factor_map[factor][x])
    return df
