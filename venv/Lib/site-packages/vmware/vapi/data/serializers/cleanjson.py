# -*- coding: utf-8 -*-

"""
Serializer vAPI data values to clean (human readable/writable) json documents
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015-2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long


import base64
import decimal
import json
import six

from vmware.vapi.data.value import (
    StructValue, ErrorValue, ListValue, OptionalValue, VoidValue, StringValue,
    BooleanValue, IntegerValue, DoubleValue, BlobValue, SecretValue)
from vmware.vapi.exception import CoreException
from vmware.vapi.lib.jsonlib import canonicalize_double
from vmware.vapi.lib.log import get_vapi_logger
from vmware.vapi.l10n.runtime import message_factory

logger = get_vapi_logger(__name__)


class DataValueToJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that converts vAPI runtime values directly
    into JSON string representation.
    """
    # Even though __init__ is called below, pylint throws a warning
    # that base class __init__ is not called (W0231)
    def __init__(self, *args, **kwargs):  # pylint: disable=W0231
        self._dispatch_map = {
            list: self.visit_list,
            decimal.Decimal: canonicalize_double,
            StructValue: self.visit_struct_value,
            ErrorValue: self.visit_struct_value,
            ListValue: self.visit_list,
            OptionalValue: self.visit_optional_value,
            DoubleValue: self.visit_double_value,
            IntegerValue: self.visit_primitive_value,
            BooleanValue: self.visit_primitive_value,
            StringValue: self.visit_primitive_value,
            VoidValue: self.visit_primitive_value,
            BlobValue: self.visit_blob_value,
            SecretValue: self.visit_primitive_value,
        }
        json.JSONEncoder.__init__(self, *args, **kwargs)

    #
    # Even though the recommended way to subclass JSONEncoder is by overriding
    # "default", encode is being used as it will preserve the computed JSON
    # string literal for decimals. If we use default, the value returned by
    # canonicalize_double will be wrapped inside double quotes in the final
    # JSON message.
    #
    def encode(self, value):
        """
        Encode a given vAPI runtime object

        :type  value: :class:`object`
        :param value: vAPI runtime object
        :rtype: :class:`str`
        :return: JSON string
        """
        return self._dispatch_map.get(type(value), self.visit_default)(value)

    def visit_struct_value(self, value):
        """
        Visit a StructValue object

        :type  value: :class:`vmware.vapi.data.value.StructValue`
        :param value: Struct value object
        :rtype: :class:`str`
        :return: JSON string
        """
        items = {}
        for field_name, field_value in value.get_fields():
            # Omit unset optional values
            if (isinstance(field_value, OptionalValue)
                    and not field_value.is_set()):
                continue
            items[field_name] = field_value
        items = ['"%s":%s' % (k, self.encode(v))
                 for k, v in six.iteritems(items)]
        return '{%s}' % (','.join(items))

    def visit_list(self, value):
        """
        Visit a ListValue object

        :type  value: :class:`vmware.vapi.data.value.ListValue`
        :param value: List value object
        :rtype: :class:`str`
        :return: JSON string
        """
        string = ','.join([self.encode(item)
                          for item in value])
        return '[%s]' % string

    def visit_optional_value(self, value):
        """
        Visit a OptionalValue object

        :type  value: :class:`vmware.vapi.data.value.OptionalValue`
        :param value: Optional value object
        :rtype: :class:`str`
        :return: JSON string
        """
        if value.is_set():
            return '%s' % self.encode(value.value)
        else:
            return 'null'

    @staticmethod
    def visit_double_value(value):
        """
        Visit a DoubleValue object

        :type  value: :class:`vmware.vapi.data.value.DoubleValue`
        :param value: Double value object
        :rtype: :class:`str`
        :return: JSON string
        """
        return canonicalize_double(value.value)

    def visit_primitive_value(self, value):
        """
        Visit one of StringValue, IntegerValue, BooleanValue or VoidValue

        :type  value: :class:`vmware.vapi.data.value.StringValue` (or)
            :class:`vmware.vapi.data.value.IntegerValue` (or)
            :class:`vmware.vapi.data.value.BooleanValue` (or)
            :class:`vmware.vapi.data.value.VoidValue` (or)
        :param value: StringValue, IntegerValue, BooleanValue or
                      VoidValue object
        :rtype: :class:`str`
        :return: JSON string
        """
        return json.JSONEncoder.encode(self, value.value)

    def visit_blob_value(self, value):
        """
        Visit BlobValue

        :type  value: :class:`vmware.vapi.data.value.BlobValue`
        :param value: BlobValue object
        :rtype: :class:`str`
        :return: JSON string
        """
        base64_encoded_value = base64.b64encode(value.value)
        data_value = base64_encoded_value.decode()

        return json.JSONEncoder.encode(self, data_value)

    def visit_default(self, value):
        """
        This is the default visit method if the type of the input value
        does not match any type in the keys present in dispatch map.

        :type  value: :class:`object`
        :param value: Python object
        :rtype: :class:`str`
        :return: JSON string
        """
        return json.JSONEncoder.encode(self, value)


class DataValueToRestJSONEncoder(DataValueToJSONEncoder):
    """
    Custom JSON encoder that converts vAPI runtime values directly
    into REST 2018 JSON string representation.
    """
    def __init__(self, *args, **kwargs):  # pylint: disable=W0231
        DataValueToJSONEncoder.__init__(self, *args, **kwargs)

    def visit_list(self, value):
        """
        Visit a ListValue object

        :type  value: :class:`vmware.vapi.data.value.ListValue`
        :param value: List value object
        :rtype: :class:`str`
        :return: JSON string
        """
        if value.is_map():
            string = ','.join([self.map_entry(item)
                              for item in value])
            return '{%s}' % string
        else:
            return DataValueToJSONEncoder.visit_list(self, value)

    def map_entry(self, value):
        """
        Visit a StructValue object

        :type  value: :class:`vmware.vapi.data.value.StructValue`
        :param value: Struct value object
        :rtype: :class:`str`
        :return: JSON string
        """
        k = value.get_field('key')
        v = value.get_field('value')
        return '%s: %s' % (self.encode(k), self.encode(v))


class JsonDictToVapi(object):
    """ Clean Json dict to vapi data value """
    def __init__(self):
        self._dispatch_map = {
            dict: self._visit_dict,
            list: self._visit_list,
            six.text_type: self._visit_string,
            bool: self._visit_bool,
            decimal.Decimal: self._visit_float,
            type(None): self._visit_none
        }
        for int_type in six.integer_types:
            self._dispatch_map[int_type] = self._visit_int

    def data_value(self, obj):
        """
        Convert json object to data value

        :type  obj: :class:`object`
        :param obj: Python object
        :rtype: :class:`vmware.vapi.data.value.DataValue`
        :return: Data value
        """
        return self._visit(obj)

    def _visit(self, obj):
        """
        Visit json object

        :type  obj: :class:`object`
        :param obj: Python object
        :rtype: :class:`vmware.vapi.data.value.DataValue`
        :return: Data value
        """
        obj_type = type(obj)
        if obj_type not in self._dispatch_map:
            msg = message_factory.get_message(
                'vapi.data.serializers.invalid.type', obj_type)
            raise CoreException(msg)
        return self._dispatch_map.get(type(obj))(obj)

    def _visit_dict(self, obj):
        """
        Visit python dictionary object

        :type  obj: :class:`dict`
        :param obj: Python dictionary object
        :rtype: :class:`vmware.vapi.data.value.StructValue`
        :return: Struct value
        """
        result = StructValue()
        for k, v in six.iteritems(obj):
            result.set_field(k, self._visit(v))
        return result

    def _visit_list(self, obj):
        """
        Visit python list object

        :type  obj: :class:`list`
        :param obj: Python list object
        :rtype: :class:`vmware.vapi.data.value.ListValue`
        :return: List value
        """
        list_val = [self._visit(o) for o in obj]
        return ListValue(list_val)

    def _visit_string(self, obj):  # pylint: disable=R0201
        """
        Visit python string object

        :type  obj: :class:`unicode` for Python 2 and :class:`str` for Python 3
        :param obj: Python string object
        :rtype: :class:`vmware.vapi.data.value.StringValue`
        :return: String value
        """
        return StringValue(obj)

    def _visit_int(self, obj):  # pylint: disable=R0201
        """
        Visit python int object

        :type  obj: :class:`int` or :class:`long` for Python 2 and :class:`int`
                    for Python 3
        :param obj: Python integer object
        :rtype: :class:`vmware.vapi.data.value.IntegerValue`
        :return: Integer value
        """
        return IntegerValue(obj)

    def _visit_bool(self, obj):  # pylint: disable=R0201
        """
        Visit python boolean object

        :type  obj: :class:`bool`
        :param obj: Python boolean object
        :rtype: :class:`vmware.vapi.data.value.BooleanValue`
        :return: Boolean value
        """
        return BooleanValue(obj)

    def _visit_float(self, obj):  # pylint: disable=R0201
        """
        Visit python Decimal object

        :type  obj: :class:`decimal.Decimal`
        :param obj: Python Decimal object
        :rtype: :class:`vmware.vapi.data.value.DoubleValue`
        :return: Double value
        """
        return DoubleValue(obj)

    def _visit_none(self, obj):  # pylint: disable=R0201,W0613
        """
        Visit python None object

        :type  obj: :class:`NoneType`
        :param obj: Python None object
        :rtype: :class:`vmware.vapi.data.value.OptionalValue`
        :return: Optional value
        """
        return OptionalValue()


class DataValueConverter(object):
    """
    Converter class that converts values from vAPI DataValue to clean
    JSON objects and back.
    """
    @staticmethod
    def convert_to_json(data_value, new_rest=False):
        """
        Convert the given data value to a JSON string representation

        :type  data_value: :class:`vmware.vapi.data.value.DataValue`
        :param data_value: Data value to be converted
        :type  new_rest: :class:`bool`
        :param new_rest: Is it a REST 2018 call
        :rtype: :class:`str`
        :return: JSON representation of the data value
        """
        if new_rest:
            encoder = DataValueToRestJSONEncoder
        else:
            encoder = DataValueToJSONEncoder
        return json.dumps(data_value,
                          check_circular=False,
                          separators=(',', ':'),
                          cls=encoder)

    @staticmethod
    def convert_to_data_value(json_string):
        """
        Convert the given json string to data value

        :type  json_string: :class:`str`
        :param json_string: JSON representation of the data value
        :rtype: :class:`vmware.vapi.data.value.DataValue`
        :return: Data value
        """
        json_dict = json.loads(json_string, parse_float=decimal.Decimal)
        return JsonDictToVapi().data_value(json_dict)
