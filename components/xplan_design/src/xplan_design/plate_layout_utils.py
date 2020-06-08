import pandas as pd
import logging


l = logging.getLogger(__file__)
l.setLevel(logging.INFO)


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
                    samples.loc[:, factor] = None      
    
    return samples

def get_factor_from_condition_set(factor_id, condition_set):
    for cs_factor in condition_set['factors']:
        if cs_factor['factor'] == factor_id:
            return cs_factor
    return None
    #raise Exception("Could not find factor %s in condition_set %s", factor_id, condition_set)

def condition_set_is_singletons(factors, condition_set):
    for factor_id in factors:
        factor = get_factor_from_condition_set(factor_id, condition_set)
        if factor is not None and  len(factor['values']) != 1:
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
