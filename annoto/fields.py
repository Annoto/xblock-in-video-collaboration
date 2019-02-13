import six
from xblock.fields import JSONField, UNSET, Scope


class NamedBoolean(JSONField):
    '''Custom boolean field with named choices'''
    MUTABLE = False

    def __init__(self, help=None, default=UNSET, scope=Scope.content,
                 display_name=None, display_true='True', display_false='False', **kwargs):
        default = default and 1 or 0
        super(NamedBoolean, self).__init__(help=help, default=default, scope=scope, display_name=display_name,
                                      values=({'display_name': display_true, 'value': '1'},
                                              {'display_name': display_false, 'value': '0'}),
                                      **kwargs)

    def read_from(self, xblock):
        val = self.__get__(xblock, xblock.__class__)
        return val and 1 or 0

    def from_json(self, value):
        if isinstance(value, six.binary_type):
            value = value.decode('ascii', errors='replace')
        if isinstance(value, six.text_type):
            return value.lower() == 'true'
        else:
            return bool(value)

    enforce_type = from_json
