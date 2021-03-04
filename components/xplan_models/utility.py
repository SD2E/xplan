import logging

l = logging.getLogger(__file__)
l.setLevel(logging.INFO)

class UtilityFunction(dict):
    LINEAR = 'Linear'

    def __init__(self,  **kwargs):
        super(UtilityFunction, self).__init__( **kwargs)
        self['factors'] = kwargs['factors'].copy()
    
    def createUtilityFunction(**kwargs):
        utility = kwargs['utility']
        if utility == UtilityFunction.LINEAR:
            return LinearUtilityFunction(**kwargs)
        raise Exception("Unknown UtilityFunction: " + str(utility))


class LinearUtilityFunction(UtilityFunction):
    def __init__(self,  **kwargs):
        super(LinearUtilityFunction, self).__init__( **kwargs)
         

    def value_of(self, x):
        l.debug("value_of: " + str(x))
        value = 0.0
        for f in self['factors'].values():
            if f['dtype'] == "float":
                [lb, ub] = f.get_discretization_names()
                cols = [x[lb], x[ub]]
                l.debug("Getting Value of: " + str(cols))
                value = value + (f.weight() * f['utility_obj'].value_of(cols))
            else:
                col = x[f.get_discretization_names()].item()
                l.debug("Getting Value of: " + str(col))
                value = value + (f.weight() * f['utility_obj'].value_of(col))
        return value

class Utility(dict):
    UNIFORM = "Uniform"
    
    def __init__(self,  **kwargs):
        super(Utility, self).__init__( **kwargs)
        
    def createUtility( **kwargs):
        utility = kwargs['factor']['utility']
        if type(utility) is str:
            if utility == Utility.UNIFORM:
                return UniformUtility(**kwargs)
        elif type(utility) is dict:
            if kwargs['factor']['dtype'] == "str":
                return DiscreteCategoricalUtility(**kwargs)
            else:
                return DiscretedUtility(**kwargs)
        raise Exception("Unknown Utility: " + str(utility))

    def value_of(self, x):
        pass
    
class UniformUtility(Utility):
    def __init__(self,  **kwargs):
        super(UniformUtility, self).__init__( **kwargs)
        l.debug("UniformUtility(): "  + str(kwargs))
        self['utility'] = 1.0 / len(self['factor']['domain'])
        
    def value_of(self, x):
        return self['utility']


class DiscreteCategoricalUtility(Utility):
    def __init__(self, **kwargs):
        super(DiscreteCategoricalUtility, self).__init__(**kwargs)
        l.debug("DiscreteCategoricalUtility(): " + str(kwargs))
        self['values'] = kwargs['factor']['utility']

    def value_of(self, x):
        return self['values'][x]
    
class DiscretedUtility(Utility):
    def __init__(self, **kwargs):
        super(DiscretedUtility, self).__init__(**kwargs)
        l.debug("DiscretedUtility(): " + str(kwargs))
        self['values'] = kwargs['factor']['utility']

    def value_of(self, x):
        if type(x) is list:
            [x_lb, x_ub] = x

            for k,v in self['values'].items():
                [lb, ub] = eval(k)
                if lb <= x_lb and x_ub <= ub:
                    return v
        else:
            for k,v in self['values'].items():
                [lb, ub] = eval(k)
                if lb <= x and x < ub:
                    return v
        raise Exception("Cannot find value for " + str(x) + " in " + str(values))
            
