"""
Convenience methods to convert to/from python native values to data values
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import datetime
import six

from vmware.vapi.data.type import Type
from vmware.vapi.data.definition import BooleanDefinition, DoubleDefinition, \
    DynamicStructDefinition, IntegerDefinition, ListDefinition, \
    OptionalDefinition, StringDefinition
from vmware.vapi.data.value import OptionalValue, StructValue
from vmware.vapi.exception import CoreException
from vmware.vapi.bindings.struct import VapiStruct
from vmware.vapi.l10n.runtime import message_factory
from vmware.vapi.lib.constants import DYNAMIC_STRUCTURE
from vmware.vapi.lib.converter import Converter


# Map from vAPI types to Python native types
_py_type_map = {
    Type.STRING: str,
    Type.BOOLEAN: bool,
    Type.DOUBLE: float,
    Type.SECRET: str,
}
if six.PY2:
    _py_type_map[Type.INTEGER] = long
else:
    _py_type_map[Type.INTEGER] = int

# Map from Python native types to vAPI data definitions
_py_to_data_def_map = {
    str: StringDefinition,
    int: IntegerDefinition,
    float: DoubleDefinition,
    bool: BooleanDefinition,
    datetime.datetime: StringDefinition,
}

if six.PY2:
    _py_to_data_def_map[unicode] = StringDefinition
    _py_to_data_def_map[long] = IntegerDefinition


def build_data_value(py_value, data_def):
    """
    Converts a native python value to data value
    using the provided data definition

    :type  py_value: :class:`object`
    :param py_value: Python native value
    :type  data_def: :class:`vmware.vapi.data.definition.DataDefinition`
    :param data_def: Data definition
    :rtype: :class:`vmware.vapi.data.value.DataValue`
    :return: Data value
    """
    output_val = None
    if data_def.type == Type.OPTIONAL:
        output_val = data_def.new_value()
        if py_value is not None:
            output_val.value = build_data_value(py_value,
                                                data_def.element_type)
    elif data_def.type == Type.LIST:
        output_val = data_def.new_value()
        if py_value:
            for output in py_value:
                output_val.add(build_data_value(output, data_def.element_type))
    elif data_def.type in (Type.STRUCTURE, Type.ERROR):
        output_val = data_def.new_value()
        for field in data_def.get_field_names():
            field_def = data_def.get_field(field)

            if py_value is None:
                if field_def.type == Type.OPTIONAL:
                    output_val.set_field(field,
                                         OptionalValue())
                else:
                    msg = message_factory.get_message(
                        'vapi.data.structure.field.missing', data_def.name,
                        field)
                    raise CoreException(msg)
            else:
                if isinstance(py_value, dict):
                    value = py_value.get(field)
                elif isinstance(py_value, VapiStruct):
                    # If Class used in python bindings is the struct
                    value = py_value.get_field(field)
                else:
                    msg = message_factory.get_message(
                        'vapi.data.structure.field.invalid', field)
                    raise CoreException(msg)
                output_val.set_field(
                    field, build_data_value(value, data_def.get_field(field)))
    elif data_def.type == Type.DYNAMIC_STRUCTURE:
        output_val = StructValue(DYNAMIC_STRUCTURE)
        if isinstance(py_value, dict):
            for key, val in six.iteritems(py_value):
                if val is None:
                    field_data_def = OptionalDefinition(StringDefinition())
                elif isinstance(val, list):
                    if len(val) == 0:
                        # empty list
                        field_data_def = ListDefinition(StringDefinition())
                    else:
                        # at least one element
                        field_data_def = ListDefinition(
                            _py_to_data_def_map.get(type(val[0]))())
                elif isinstance(val, dict):
                    field_data_def = DynamicStructDefinition()
                else:
                    try:
                        # Field is probably a primitive/atomic type
                        field_data_def_type = _py_to_data_def_map[type(val)]
                        field_data_def = field_data_def_type()
                    except KeyError:
                        msg = message_factory.get_message(
                                'vapi.data.serializers.python.unsupported.'
                                'python.type',
                                type(val), key)
                        raise CoreException(msg)
                output_val.set_field(key, build_data_value(val, field_data_def))
    elif data_def.type == Type.VOID:
        output_val = data_def.new_value()
    elif data_def.type == Type.OPAQUE:
        output_val = py_value
    # Primitive type Integer/Double/String/Boolean/Secret
    else:
        output_val = data_def.new_value(py_value)
    return output_val


def _pepify_args(meth_args):
    """
    Pepify the names of the method arguments

    :type  meth_args: :class:`dict`
    :param meth_args: Actual method arguments
    :rtype: :class:`dict`
    :return: Modified method arguments with pepified names
    """
    new_args = {}
    for k, v in six.iteritems(meth_args):
        new_args[Converter.pepify(k)] = v
    return new_args


def _build_py_value(data_value, data_def, impl=None):
    """"
    Converts a data value to python native value
    impl input is required to create Struct class instances

    :type  data_value: :class:`vmware.vapi.data.value.DataValue`
    :param data_value: Input data value
    :type  data_def: :class:`vmware.vapi.data.definition.DataDefinition`
    :param data_def: Data definition
    :type  impl: :class:`vmware.vapi.bindings.stub.VapiInterface` or
        :class:`vmware.vapi.bindings.skeleton.VapiInterface` or ``None``
    :param impl: Python generated class to resolve structure classes
    :rtype: :class:`object`
    :return: Native python value
    """
    if data_def.type == Type.OPTIONAL:
        if data_value.is_set():
            element_def = data_def.element_type
            element_value = data_value.value
            py_value = _build_py_value(element_value, element_def, impl)
        else:
            py_value = None
    elif data_def.type == Type.LIST:
        py_value = []
        element_def = data_def.element_type
        for element_value in data_value:
            py_value.append(_build_py_value(element_value, element_def, impl))
    elif data_def.type in (Type.STRUCTURE, Type.ERROR):
        struct_name = data_def.name
        class_name = Converter.underscore_to_capwords(struct_name)
        py_value = {}
        for field in data_def.get_field_names():
            field_def = data_def.get_field(field)
            field_val = data_value.get_field(field)
            py_value[field] = _build_py_value(field_val, field_def, impl)
        if impl and hasattr(impl, class_name):
            kwargs = _pepify_args(py_value)
            py_value = getattr(impl, class_name)(**kwargs)
    elif data_def.type == Type.VOID:
        py_value = None
    # For opaque value, no need of any conversion
    elif data_def.type == Type.OPAQUE:
        py_value = data_value
    # Primitive type Integer/Double/String/Boolean/Secret
    else:
        py_type = _py_type_map.get(data_def.type)
        py_value = py_type(data_value.value)
    return py_value


def build_py_value(data_value, data_def=None, impl=None):
    """"
    Converts a data value to python native value
    impl input is required to create Struct class instances

    :type  data_value: :class:`vmware.vapi.data.value.DataValue`
    :param data_value: Input data value
    :type  data_def: :class:`vmware.vapi.data.definition.DataDefinition` or
        ``None``
    :param data_def: Data definition
    :type  impl: :class:`vmware.vapi.bindings.stub.VapiInterface` or
        :class:`vmware.vapi.bindings.skeleton.VapiInterface` or ``None``
    :param impl: Python generated class to resolve structure classes
    :rtype: :class:`object`
    :return: Native python value
    """
    if data_def is None:
        raise Exception('Data definition is required')
    return _build_py_value(data_value, data_def, impl)
