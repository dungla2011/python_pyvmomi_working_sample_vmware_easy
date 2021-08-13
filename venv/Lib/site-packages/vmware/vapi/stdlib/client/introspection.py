"""
Introspection services
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015, 2017, 2019 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

from com.vmware.vapi.std.introspection_client import Operation
from vmware.vapi.core import (
    InterfaceIdentifier, MethodIdentifier, MethodDefinition)
from vmware.vapi.data.serializers.introspection import (
    convert_data_value_to_data_def)
from vmware.vapi.lib.log import get_vapi_logger
from vmware.vapi.stdlib.client.factories import StubConfigurationFactory

logger = get_vapi_logger(__name__)


def opt_def(element):
    """
    Internal function to create DataDefinition for an optional element.
    :type  element: :class:`com.vmware.vapi.std.introspection_client.Operation.DataDefinition`
    :param element: element type definition
    :rtype: :class:`com.vmware.vapi.std.introspection_client.Operation.DataDefinition`
    :return: definition for optional value of element type.
    """
    return Operation.DataDefinition(
        type=Operation.DataDefinition.DataType.OPTIONAL,
        element_definition=element
    )


def list_def(element):
    """
    Internal function to create DataDefinition for a list.
    :type  element: :class:`com.vmware.vapi.std.introspection_client.Operation.DataDefinition`
    :param element: list element type definition
    :rtype: :class:`com.vmware.vapi.std.introspection_client.Operation.DataDefinition`
    :return: definition for a list of element values.
    """
    return Operation.DataDefinition(
        type=Operation.DataDefinition.DataType.LIST,
        element_definition=element
    )


def map_def(key, value):
    """
    Internal function to create map definition from a key and value definitions
    definitions. For use only by vAPI runtime.
    :type  key: :class:`com.vmware.vapi.std.introspection_client.Operation.DataDefinition`
    :param key: DataDefintion for the map key
    :type  value: :class:`com.vmware.vapi.std.introspection_client.Operation.DataDefinition`
    :param value: DataDefintion for the map value
    :rtype: :class:`com.vmware.vapi.std.introspection_client.Operation.DataDefinition`
    :return: structure reference definition used to break circular references.
    """
    return list_def(
        Operation.DataDefinition(
            type=Operation.DataDefinition.DataType.STRUCTURE,
            name='map-entry',
            fields={
                'key': key,
                'value': value
            }
        )
    )


def struct_ref_def(name):
    """
    Internal function to create structure reference from name.
    :type  name: :`str`
    :param name: name of the referred to structure
    :rtype: :class:`com.vmware.vapi.std.introspection_client.Operation.DataDefinition`
    :return: structure reference definition used to break circular references.
    """
    return Operation.DataDefinition(
        type=Operation.DataDefinition.DataType.STRUCTURE_REF,
        name=name
    )


string_def = Operation.DataDefinition(
    type=Operation.DataDefinition.DataType.STRING
)

optional_string_def = opt_def(string_def)

optional_long_def = opt_def(
    Operation.DataDefinition(
        type=Operation.DataDefinition.DataType.LONG
    )
)

optional_double_def = opt_def(
    Operation.DataDefinition(
        type=Operation.DataDefinition.DataType.DOUBLE
    )
)

_LOCALIZATION_PARAM = 'com.vmware.vapi.std.localization_param'
_NESTED_LOCALIZABLE_MESSAGE = 'com.vmware.vapi.std.nested_localizable_message'
_LOCALIZABLE_MESSAGE = 'com.vmware.vapi.std.localizable_message'

nested_localizable_message_def = Operation.DataDefinition(
    type=Operation.DataDefinition.DataType.STRUCTURE,
    name=_NESTED_LOCALIZABLE_MESSAGE,
    fields={
        'id': string_def,
        'params': opt_def(map_def(string_def,
                                  struct_ref_def(_LOCALIZATION_PARAM)))
    }
)

localization_param_def = Operation.DataDefinition(
    type=Operation.DataDefinition.DataType.STRUCTURE,
    name=_LOCALIZATION_PARAM,
    fields={
        's': optional_string_def,
        'dt': optional_string_def,
        'i': optional_long_def,
        'd': optional_double_def,
        'l': opt_def(nested_localizable_message_def),
        'precision': optional_long_def,
        'format': optional_string_def
    }
)

localizable_message_def = Operation.DataDefinition(
    type=Operation.DataDefinition.DataType.STRUCTURE,
    name=_LOCALIZABLE_MESSAGE,
    fields={
        'default_message': string_def,
        'args': list_def(string_def),
        'id': string_def,
        'localized': optional_string_def,
        'params': opt_def(map_def(string_def, localization_param_def))
    }
)


def make_introspection_error_def(error_name):
    """
    Create an instance of
    :class:`com.vmware.vapi.std.introspection_client.Operation.DataDefinition` that
    represents the standard error specified

    :type  error_name: :class:`str`
    :param error_name: Fully qualified error name of one of the vAPI standard errors
    :rtype: :class:`com.vmware.vapi.std.introspection_client.Operation.DataDefinition`
    :return: Error definition instance for the given error name
    """
    return Operation.DataDefinition(
        type=Operation.DataDefinition.DataType.ERROR,
        name=error_name,
        fields={
            'messages': list_def(localizable_message_def),
            'data': opt_def(Operation.DataDefinition(
                    type=Operation.DataDefinition.DataType.DYNAMIC_STRUCTURE)
            ),
            'error_type': optional_string_def
        }
    )


class IntrospectableApiProvider(object):
    """
    Helper class for invoking the 'get' operation in the service
    'com.vmware.vapi.std.introspection.Operation'
    """
    def __init__(self, connector):
        """
        Initialize IntrospectableApiProvider

        :type  connector: :class:`vmware.vapi.protocol.client.connector.Connector`
        :param Connector: Protocol connector to use for operation invocations
        """
        stub_config = StubConfigurationFactory.new_std_configuration(connector)
        self._operation = Operation(stub_config)

    def get_method(self, service_id, operation_id):
        """
        Get method definition for the specified operation

        :type  service_id: :class:`str`
        :param service_id: Service identifier
        :type  operation_id: :class:`str`
        :param operation_id: Operation identifier
        :rtype: :class:`vmware.vapi.core.MethodDefinition`
        :return: Method definition of the specified operation
        """
        info = self._operation.get(service_id=service_id,
                                   operation_id=operation_id)
        input_def = convert_data_value_to_data_def(
            info.input_definition.get_struct_value())
        output_def = convert_data_value_to_data_def(
            info.output_definition.get_struct_value())
        error_defs = [convert_data_value_to_data_def(error_def.get_struct_value())
                      for error_def in info.error_definitions]
        interface_id = InterfaceIdentifier(service_id)
        method_id = MethodIdentifier(interface_id, operation_id)
        method_definition = MethodDefinition(method_id,
                                             input_def,
                                             output_def,
                                             error_defs)
        return method_definition
