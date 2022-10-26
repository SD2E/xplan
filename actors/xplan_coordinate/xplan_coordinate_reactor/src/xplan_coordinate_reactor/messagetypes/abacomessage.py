import os
import json
from attrdict import AttrDict
from jsonschema import validate, FormatChecker, ValidationError
from pkg_resources import resource_filename

class AbacoMessageError(Exception):
    pass


class UnknownMessageSource(AbacoMessageError):
    pass


class AbacoMessage(object):

    PARAMS = [('message', True, 'body', {}),
              ('status', False, 'status', 'CREATED'),
              ('session', False, 'session', None)]

    def __init__(self, **kwargs):
        for param, mandatory, attr, default in self.PARAMS:
            try:
                value = (kwargs[param] if mandatory
                         else kwargs.get(param, default))
            except KeyError:
                raise AbacoMessageError(
                    'parameter "{}" is mandatory'.format(param))
            setattr(self, attr, value)

    def get_body(self):
        return getattr(self, "body")

    def process_message(self, r, timestamp, *, user_data=None):
        raise AbacoMessageError(
            "process_message called on base abaco message type")

    def finalize_message(self, r, job, process_data, *, user_data=None):
        raise AbacoMessageError(
            "finalize_message called on base abaco message type")

    @classmethod
    def validate(cls, jsondata):
        """Return True is message is valid according to JSON schema"""
        HERE = os.path.abspath(__file__)
        PARENT = os.path.dirname(HERE)
        schema_name = cls.__name__ + '.jsonschema'
        schema_path = os.path.join(PARENT, "schema", schema_name)

        try:
            with open(schema_path) as schema:
                schema_json = json.loads(schema.read())
                # print(schema_json)
        except Exception as e:
            raise Exception("Schema load error", e)

        class formatChecker(FormatChecker):
            def __init__(self):
                FormatChecker.__init__(self)

        try:
            validate(jsondata, schema_json)
            return True
        except ValidationError as e:
            # print(e)
            return False
        except Exception:
            raise
