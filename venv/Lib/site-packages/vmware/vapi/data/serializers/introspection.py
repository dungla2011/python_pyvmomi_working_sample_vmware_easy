"""
Convenient libraries for introspection data
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015, 2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long


from vmware.vapi.data.definition import (
    IntegerDefinition, DoubleDefinition, BooleanDefinition, StringDefinition,
    BlobDefinition, ListDefinition, StructDefinition, OptionalDefinition,
    VoidDefinition, OpaqueDefinition, SecretDefinition, ErrorDefinition,
    StructRefDefinition, DynamicStructDefinition, AnyErrorDefinition,
    ReferenceResolver
)
from vmware.vapi.data.type import Type
from vmware.vapi.data.value import (
    StringValue, ListValue, StructValue, OptionalValue)
from vmware.vapi.exception import CoreException
from vmware.vapi.lib.constants import (Introspection, MAP_ENTRY)
from vmware.vapi.lib.log import get_vapi_logger
from vmware.vapi.l10n.runtime import message_factory

logger = get_vapi_logger(__name__)
# Type map from Type constants in runtime to
# type constants in Introspection service
data_type_map = {
    Type.INTEGER: 'LONG',
    Type.DOUBLE: 'DOUBLE',
    Type.BOOLEAN: 'BOOLEAN',
    Type.STRING: 'STRING',
    Type.BLOB: 'BINARY',
    Type.LIST: 'LIST',
    Type.STRUCTURE: 'STRUCTURE',
    Type.OPTIONAL: 'OPTIONAL',
    Type.VOID: 'VOID',
    Type.OPAQUE: 'OPAQUE',
    Type.SECRET: 'SECRET',
    Type.ERROR: 'ERROR',
    Type.STRUCTURE_REF: 'STRUCTURE_REF',
    Type.DYNAMIC_STRUCTURE: 'DYNAMIC_STRUCTURE',
    Type.ANY_ERROR: 'ANY_ERROR',
}
# Type map from type enum constants in Introspection
# service to DataDefinition objects
reverse_data_type_map = {
    'LONG': IntegerDefinition,
    'DOUBLE': DoubleDefinition,
    'BOOLEAN': BooleanDefinition,
    'STRING': StringDefinition,
    'BINARY': BlobDefinition,
    'LIST': ListDefinition,
    'STRUCTURE': StructDefinition,
    'OPTIONAL': OptionalDefinition,
    'VOID': VoidDefinition,
    'OPAQUE': OpaqueDefinition,
    'SECRET': SecretDefinition,
    'ERROR': ErrorDefinition,
    'STRUCTURE_REF': StructRefDefinition,
    'DYNAMIC_STRUCTURE': DynamicStructDefinition,
    'ANY_ERROR': AnyErrorDefinition,
}


def convert_data_def_to_data_value(data_def):
    """
    Convert :class:`vmware.vapi.data.definition.DataDefinition` object to
    :class:`vmware.vapi.data.value.DataValue` object. The type of the object
    returned is a struct value that corresponds to DataDefinition VMODL2 type
    present in introspection service.

    :type  data_def: :class:`vmware.vapi.data.definition.DataDefinition`
    :param data_def: Data definition
    :rtype: :class:`vmware.vapi.data.value.DataValue`
    :return: Data value representing the data definition object
    """
    result = StructValue(Introspection.DATA_DEFINITION)
    result.set_field(
        'type', StringValue(data_type_map.get(data_def.type)))

    if (data_def.type == Type.STRUCTURE or
            data_def.type == Type.STRUCTURE_REF or
            data_def.type == Type.ERROR):
        result.set_field('name', OptionalValue(StringValue(data_def.name)))
    else:
        result.set_field('name', OptionalValue())

    if (data_def.type == Type.OPTIONAL or
            data_def.type == Type.LIST):
        element_definition = data_def.element_type
        element_value = convert_data_def_to_data_value(
            element_definition)
        result.set_field('element_definition',
                         OptionalValue(element_value))
    else:
        result.set_field('element_definition', OptionalValue())

    if (data_def.type == Type.STRUCTURE or data_def.type == Type.ERROR):
        fields = ListValue()
        for field_name in data_def.get_field_names():
            element_definition = data_def.get_field(field_name)
            field_pair = StructValue(MAP_ENTRY)
            field_pair.set_field('key', StringValue(field_name))
            field_pair.set_field(
                'value',
                convert_data_def_to_data_value(element_definition))
            fields.add(field_pair)
        result.set_field('fields', OptionalValue(fields))
    else:
        result.set_field('fields', OptionalValue())
    return result


def _convert_data_value_to_data_def_int(data_value, ctx):
    """
    Convert :class:`vmware.vapi.data.value.DataValue` object that
    corresponds to DataDefinition structure in introspection VMODL2 into
    :class:`vmware.vapi.data.definition.DataDefinition` object using the
    ReferenceResolver context.

    ReferenceResolver is used to resolve any STRUCTURE_REF objects present in
    the input value. This function registers all the STRUCTURE and
    STRUCTURE_REF objects with ReferenceResolver. The caller of this function
    must call "resolve()" on the ReferenceResolver to resolve the
    StructDefinition references in StructRefDefinition

    :type  data_value: :class:`vmware.vapi.data.value.DataValue`
    :param data_value: Data value representing the data definition object
    :type  ctx: :class:`vmware.vapi.data.definition.ReferenceResolver`
    :param ctx: Context to resolve structure reference definitions
    :rtype: :class:`vmware.vapi.data.definition.DataDefinition`
    :return: Data definition
    """
    type_name = data_value.get_field('type').value
    data_def_class = reverse_data_type_map.get(type_name)
    # Primitive types
    if type_name in ['VOID', 'LONG', 'DOUBLE', 'STRING', 'OPAQUE',
                     'BOOLEAN', 'SECRET', 'BINARY',
                     'DYNAMIC_STRUCTURE', 'ANY_ERROR']:
        return data_def_class()
    # Generic types
    elif type_name in ['OPTIONAL', 'LIST']:
        element_type_def = _convert_data_value_to_data_def_int(
            data_value.get_field('element_definition').value, ctx)
        return data_def_class(element_type_def)
    # Struct Ref definition
    elif type_name == 'STRUCTURE_REF':
        data_def = data_def_class(data_value.get_field('name').value.value)
        ctx.add_reference(data_def)
        return data_def
    # Structure and Error types
    elif type_name in ['STRUCTURE', 'ERROR']:
        name = data_value.get_field('name').value.value
        field_defs = []
        fields = data_value.get_field('fields').value
        for field_info in fields:
            field_name = field_info.get_field('key').value
            field_def = _convert_data_value_to_data_def_int(
                field_info.get_field('value'), ctx)
            field_defs.append((field_name, field_def))
        data_def = data_def_class(name, field_defs)
        ctx.add_definition(data_def)
        return data_def
    else:
        msg = message_factory.get_message(
            'vapi.introspection.invalid.type', type_name)
        logger.debug(msg)
        raise CoreException(msg)


def convert_data_value_to_data_def(data_value):
    """
    Convert :class:`vmware.vapi.data.value.DataValue` object that
    corresponds to DataDefinition structure in introspection VMODL2 into
    :class:`vmware.vapi.data.definition.DataDefinition` object.

    :type  data_value: :class:`vmware.vapi.data.value.DataValue`
    :param data_value: Data value representing the data definition object
    :rtype: :class:`vmware.vapi.data.definition.DataDefinition`
    :return: Data definition
    """
    ctx = ReferenceResolver()
    result = _convert_data_value_to_data_def_int(data_value, ctx)
    ctx.resolve()
    return result
