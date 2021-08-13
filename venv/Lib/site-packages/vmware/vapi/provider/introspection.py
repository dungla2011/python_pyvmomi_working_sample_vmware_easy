"""
Introspection services
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015, 2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

from vmware.vapi.core import (
    ApiInterface, InterfaceIdentifier, MethodIdentifier, InterfaceDefinition,
    MethodDefinition, MethodResult, ExecutionContext)
from vmware.vapi.data.definition import (
    StructDefinition, StringDefinition, ListDefinition, StructRefDefinition,
    OptionalDefinition)
from vmware.vapi.data.serializers.introspection import (
    convert_data_def_to_data_value)
from vmware.vapi.lib.constants import (
    Introspection, MAP_ENTRY, OPERATION_INPUT)
from vmware.vapi.lib.log import get_vapi_logger
from vmware.vapi.lib.std import make_error_value_from_msgs, make_std_error_def
from vmware.vapi.data.value import (
    StringValue, ListValue, StructValue)
from vmware.vapi.lib.fingerprint import generate_fingerprint
from vmware.vapi.l10n.runtime import message_factory


# errors
not_found_def = make_std_error_def('com.vmware.vapi.std.errors.not_found')

logger = get_vapi_logger(__name__)


def get_checksum(api_services):
    """
    Returns the checksum of services registered with LocalProvider

    :type  api_services: :class:`dict`
    :param api_services: Dictionary of all the services registered with local provider
        Key is :class:`vmware.vapi.core.InterfaceIdentifier` and value is
        :class:`vmware.vapi.core.ApiInterface`
    :rtype: :class:`str`
    :return: checksum of the service information
    """
    return generate_fingerprint(str(api_services))


class IntrospectionBaseApiInterface(ApiInterface):
    """
    Helper base class for all Introspection VMODL2 dynamic services
    """

    def __init__(self, iface_id, method_defs, methods):
        """
        Initialize the Api Interface instance

        :type  iface_id: :class:`vmware.vapi.core.InterfaceIdentifier`
        :param iface_id: Interface identifier
        :type  method_defs: :class:`dict`
        :param method_defs: Dictionary of method identifiers to method definitions
        :type  methods: :class:`dict`
        :param methods: Dictionary of method identifiers to method references
        """
        ApiInterface.__init__(self)
        self._id = iface_id
        self._method_defs = method_defs
        self._methods = methods

    def get_identifier(self):
        """
        Returns interface identifier

        :rtype: :class:`InterfaceIdentifier`
        :return: Interface identifier
        """
        return self._id

    def get_definition(self):
        """
        Returns interface definition

        :rtype: :class:`InterfaceDefinition`
        :return: Interface definition
        """
        return InterfaceDefinition(self._id, list(self._methods.keys()))

    def get_method_definition(self, method_id):
        """
        Returns the method definition

        :rtype: :class:`MethodDefinition`
        :return: Method definition
        """
        return self._method_defs.get(method_id)

    def invoke(self, ctx, method_id, input_value):
        """
        Invokes the specified method using the execution context and
        the input provided

        :type  ctx: :class:`ExecutionContext`
        :param ctx: Execution context for this method
        :type  method_id: :class:`MethodIdentifier`
        :param method_id: Method identifier
        :type  input_value: :class:`vmware.vapi.data.value.StructValue`
        :param input_value: Method input parameters

        :rtype: :class:`MethodResult`
        :return: Result of the method invocation
        """
        method = self._methods.get(method_id)
        method_def = self._method_defs.get(method_id)
        return method(method_def, ctx, input_value)


class ProviderApiInterface(IntrospectionBaseApiInterface):
    """
    This service provides operations to retrieve information of a
    vAPI Provider. A provider represents a vAPI endpoint that is exposing a
    collection of vAPI services.
    """

    def __init__(self, name, introspection_adapter):
        """
        Initialize ProviderApiInterface

        :type  name: :class:`str`
        :param name: Name of the provider
        :type  introspection_adapter:
            :class:`vmware.vapi.provider.introspection.ApiProviderIntrospector`
        :param introspection_adapter: Adapter for fetching introspection information
        """
        self._name = name
        self._adapter = introspection_adapter

        iface_id = InterfaceIdentifier(
            'com.vmware.vapi.std.introspection.provider')

        method_defs = {}
        # get method
        get_method_id = MethodIdentifier(iface_id, 'get')
        output_def = StructDefinition(
            'com.vmware.vapi.std.introspection.provider.info',
            [('id', StringDefinition()),
             ('checksum', StringDefinition())]
        )
        method_defs[get_method_id] = MethodDefinition(
            get_method_id,
            StructDefinition(OPERATION_INPUT, []),
            output_def,
            []
        )

        methods = {}
        methods[get_method_id] = self._get

        IntrospectionBaseApiInterface.__init__(self,
                                               iface_id,
                                               method_defs,
                                               methods)

    def _get(self, method_def, ctx, input_value):
        """
        Returns information about the vAPI provider

        :type  method_def: :class:`vmware.vapi.core.MethodDefinition`
        :param method_def: Method definition
        :type  ctx: :class:`vmware.vapi.core.ExecutionContext`
        :param ctx: Execution context
        :type  input_value: :class:`vmware.vapi.data.value.StructValue`
        :param input_value: Struct value input
        :rtype: :class:`vmware.vapi.core.MethodResult`
        :return: Information about the vAPI provider
        """
        output = method_def.get_output_definition().new_value()
        output.set_field('id', StringValue(self._name))
        output.set_field('checksum', StringValue(self._adapter.get_checksum()))
        return MethodResult(output=output)


class ServiceApiInterface(IntrospectionBaseApiInterface):
    """
    This service exposes operations to retrieve information about the
    services exposed by a vAPI endpoint
    """
    def __init__(self, name, introspection_adapter):
        """
        Initialize ServiceApiInterface

        :type  name: :class:`str`
        :param name: Name of the provider
        :type  introspection_adapter:
            :class:`vmware.vapi.provider.introspection.ApiProviderIntrospector`
        :param introspection_adapter: Adapter for fetching introspection information
        """
        self._adapter = introspection_adapter

        iface_id = InterfaceIdentifier(
            'com.vmware.vapi.std.introspection.service')
        method_defs = {}
        methods = {}

        # list method
        list_method_id = MethodIdentifier(iface_id, 'list')
        output_def = ListDefinition(StringDefinition())
        method_defs[list_method_id] = MethodDefinition(
            list_method_id,
            StructDefinition(OPERATION_INPUT, []),
            output_def,
            []
        )
        methods[list_method_id] = self._list

        # get method
        get_method_id = MethodIdentifier(iface_id, 'get')
        output_def = StructDefinition(
            'com.vmware.vapi.std.introspection.service.info',
            [('operations', ListDefinition(StringDefinition()))])
        method_defs[get_method_id] = MethodDefinition(
            get_method_id,
            StructDefinition(OPERATION_INPUT,
                             [('id', StringDefinition())]),
            output_def,
            [not_found_def]
        )
        methods[get_method_id] = self._get

        IntrospectionBaseApiInterface.__init__(self,
                                               iface_id,
                                               method_defs,
                                               methods)

    def _list(self, method_def, ctx, input_value):
        """
        Get the set of service identifiers

        :type  method_def: :class:`vmware.vapi.core.MethodDefinition`
        :param method_def: Method definition
        :type  ctx: :class:`vmware.vapi.core.ExecutionContext`
        :param ctx: Execution context
        :type  input_value: :class:`vmware.vapi.data.value.StructValue`
        :param input_value: Struct value input
        :rtype: :class:`vmware.vapi.core.MethodResult`
        :return: Set of service identifiers
        """
        output = method_def.get_output_definition().new_value()
        for service in self._adapter.get_services():
            output.add(StringValue(service))
        return MethodResult(output=output)

    def _get(self, method_def, ctx, input_value):
        """
        Returns information about specified service

        :type  method_def: :class:`vmware.vapi.core.MethodDefinition`
        :param method_def: Method definition
        :type  ctx: :class:`vmware.vapi.core.ExecutionContext`
        :param ctx: Execution context
        :type  input_value: :class:`vmware.vapi.data.value.StructValue`
        :param input_value: Struct value input
        :rtype: :class:`vmware.vapi.core.MethodResult`
        :return: Information about specified service
        """
        service_id = str(input_value.get_field('id').value)
        return self._adapter.get_service_info(service_id)


class OperationApiInterface(IntrospectionBaseApiInterface):
    """
    This service exposes a list of operations to retrieve
    information about the operations present in a vAPI service
    """
    def __init__(self, name, introspection_adapter):
        """
        Initialize OperationApiInterface

        :type  name: :class:`str`
        :param name: Name of the provider
        :type  introspection_adapter:
            :class:`vmware.vapi.provider.introspection.ApiProviderIntrospector`
        :param introspection_adapter: Adapter for fetching introspection information
        """
        self._adapter = introspection_adapter
        iface_id = InterfaceIdentifier(
            'com.vmware.vapi.std.introspection.operation')
        method_defs = {}
        methods = {}

        # list method
        list_method_id = MethodIdentifier(iface_id, 'list')
        output_def = ListDefinition(StringDefinition())
        method_defs[list_method_id] = MethodDefinition(
            list_method_id,
            StructDefinition(OPERATION_INPUT,
                             [('service_id', StringDefinition())]),
            output_def,
            [not_found_def]
        )
        methods[list_method_id] = self._list

        # get method
        get_method_id = MethodIdentifier(iface_id, 'get')
        data_ref_def = StructRefDefinition(
            'com.vmware.vapi.std.introspection.operation.data_definition')
        field_def = StructDefinition(
            MAP_ENTRY,
            [('key', StringDefinition()),
             ('value', data_ref_def)])
        data_def = StructDefinition(
            'com.vmware.vapi.std.introspection.operation.data_definition',
            [('type', StringDefinition()),
             ('element_definition', OptionalDefinition(data_ref_def)),
             ('name', OptionalDefinition(StringDefinition())),
             ('fields', OptionalDefinition(ListDefinition(field_def)))])
        data_ref_def.target = data_def
        output_def = StructDefinition(
            'com.vmware.vapi.std.introspection.operation.info',
            [('input_definition', data_def),
             ('output_definition', data_def),
             ('error_definitions', ListDefinition(data_def))])
        method_defs[get_method_id] = MethodDefinition(
            get_method_id,
            StructDefinition(OPERATION_INPUT,
                             [('service_id', StringDefinition()),
                              ('operation_id', StringDefinition())]),
            output_def,
            [not_found_def]
        )
        methods[get_method_id] = self._get

        IntrospectionBaseApiInterface.__init__(self,
                                               iface_id,
                                               method_defs,
                                               methods)

    def _list(self, method_def, ctx, input_value):
        """
        Get the set of operation identifiers

        :type  method_def: :class:`vmware.vapi.core.MethodDefinition`
        :param method_def: Method definition
        :type  ctx: :class:`vmware.vapi.core.ExecutionContext`
        :param ctx: Execution context
        :type  input_value: :class:`vmware.vapi.data.value.StructValue`
        :param input_value: Struct value input
        :rtype: :class:`vmware.vapi.core.MethodResult`
        :return: Set of operation identifiers
        """
        service_id = str(input_value.get_field('service_id').value)
        return self._adapter.get_operations(service_id)

    def _get(self, method_def, ctx, input_value):
        """
        Returns information about a vAPI operation

        :type  method_def: :class:`vmware.vapi.core.MethodDefinition`
        :param method_def: Method definition
        :type  ctx: :class:`vmware.vapi.core.ExecutionContext`
        :param ctx: Execution context
        :type  input_value: :class:`vmware.vapi.data.value.StructValue`
        :param input_value: Struct value input
        :rtype: :class:`vmware.vapi.core.MethodResult`
        :return: Information about a vAPI operation
        """
        service_id = str(input_value.get_field('service_id').value)
        operation_id = str(input_value.get_field('operation_id').value)
        return self._adapter.get_operation_info(service_id, operation_id)


class ApiProviderIntrospector(object):
    """
    Abstract class for fetching introspection information
    """
    def __init__(self, name):
        """
        Initialize ApiProviderIntrospector

        :type  name: :class:`str`
        :param name: Name of the provider
        """
        self._services = [
            ProviderApiInterface(name, self),
            ServiceApiInterface(name, self),
            OperationApiInterface(name, self)]

    def get_introspection_services(self):
        """
        Returns the list of introspection services

        :rtype: :class:`list` of :class:`vmware.vapi.core.ApiInterface`
        :return: list of introspection services
        """
        return self._services

    def get_checksum(self):
        """
        Returns the checksum of the API information available

        :rtype: :class:`str`
        :return: Checksum of the API information available
        """
        raise NotImplementedError

    def get_services(self):
        """
        Returns the list of available services

        :rtype: :class:`list` of :class:`str`
        :return: List of available services
        """
        raise NotImplementedError

    def get_service_info(self, service_id):
        """
        Get information about a particular service

        :type  service_id: :class:`str`
        :param service_id: Service identifier
        :rtype: :class:`vmware.vapi.core.MethodResult`
        :return: Introspection service info. The DataValue in the output
            represents :class:'com.vmware.vapi.std.introspection.Service.Info'
        """
        raise NotImplementedError

    def get_operations(self, service_id):
        """
        Get the list of available operations for a particular service

        :type  service_id: :class:`str`
        :param service_id: Service identifier
        :rtype: :class:`vmware.vapi.core.MethodResult`
        :return: Result that contains list of available operations. The DataValue
            in the output is list of StringValues containing the operation names.
        """
        raise NotImplementedError

    def get_operation_info(self, service_id, operation_id):
        """
        Get the operation information

        :type  service_id: :class:`str`
        :param service_id: Service identifier
        :type  operation_id: :class:`str`
        :param operation_id: Operation identifier
        :rtype: :class:`vmware.vapi.core.MethodResult`
        :return: Result that contains operation information. The DataValue in the output
             represents :class:'com.vmware.vapi.std.introspection.Operation.Info'
        """
        raise NotImplementedError


class LocalProviderIntrospector(ApiProviderIntrospector):
    """
    Specialization of :class:`vmware.vapi.provider.introspection.ApiProviderIntrospector`
    that uses data available in Local Provider to process the Introspection
    service API requests
    """
    def __init__(self, name):
        """
        Initialize LocalProviderIntrospector

        :type  name: :class:`str`
        :param name: Name of the provider
        """
        ApiProviderIntrospector.__init__(self, name)
        self._service_data = {}

    def add_service(self, service_id, api_interface):
        """
        Add a new service to the introspector

        :type  service_id: :class:`str`
        :param service_id: Service identifier
        :type  api_interface: :class:`vmware.vapi.core.ApiInterface`
        :param api_interface: ApiInterface corresponding to the service
        """
        self._service_data[service_id] = api_interface

    def get_checksum(self):
        return generate_fingerprint(str(self._service_data))

    def get_services(self):
        return list(self._service_data.keys())

    def get_service_info(self, service_id):
        service_info = self._service_data.get(service_id)
        if service_info:
            method_ids = service_info.get_definition().get_method_identifiers()
            output = StructValue(
                name='com.vmware.vapi.std.introspection.service.info',
                values={'operations': ListValue(
                    values=[StringValue(method_id.get_name())
                            for method_id in method_ids])}
            )
            return MethodResult(output=output)
        else:
            msg = message_factory.get_message(
                'vapi.introspection.service.not_found', service_id)
            error_value = make_error_value_from_msgs(not_found_def, msg)
            return MethodResult(error=error_value)

    def get_operations(self, service_id):
        service_info = self._service_data.get(service_id)
        if service_info:
            method_ids = service_info.get_definition().get_method_identifiers()
            return MethodResult(
                output=ListValue(values=[StringValue(method_id.get_name())
                                         for method_id in method_ids]))
        else:
            msg = message_factory.get_message(
                'vapi.introspection.operation.service.not_found', service_id)
            error_value = make_error_value_from_msgs(not_found_def, msg)
            return MethodResult(error=error_value)

    @staticmethod
    def _convert_method_def_to_data_value(method_def):
        """
        Converts a :class:`vmware.vapi.core.MethodDefinition` object
        to :class:`vmware.vapi.data.value.DataValue` object

        :type  method_def: :class:`vmware.vapi.core.MethodDefinition`
        :param method_def: Method definition
        :rtype: :class:`vmware.vapi.data.value.DataValue`
        :return: Data value object representing method definition
        """
        output = StructValue(
            name='com.vmware.vapi.std.introspection.operation.info',
            values={
                'input_definition': convert_data_def_to_data_value(
                    method_def.get_input_definition()),
                'output_definition': convert_data_def_to_data_value(
                    method_def.get_output_definition()),
                'error_definitions': ListValue(
                    values=[convert_data_def_to_data_value(error_def)
                            for error_def in method_def.get_error_definitions()])
            })
        return output

    def get_operation_info(self, service_id, operation_id):
        service_info = self._service_data.get(service_id)
        if service_info:
            method_ids = service_info.get_definition().get_method_identifiers()
            operation_names = [method_id.get_name()
                               for method_id in method_ids]
            if operation_id in operation_names:
                method_def = service_info.get_method_definition(
                    MethodIdentifier(InterfaceIdentifier(service_id),
                                     operation_id))
                output = self._convert_method_def_to_data_value(method_def)
                return MethodResult(output=output)
            else:
                msg = message_factory.get_message(
                    'vapi.introspection.operation.not_found',
                    operation_id,
                    service_id)
                error_value = make_error_value_from_msgs(not_found_def, msg)
                return MethodResult(error=error_value)
        else:
            msg = message_factory.get_message(
                'vapi.introspection.operation.service.not_found', service_id)
            error_value = make_error_value_from_msgs(not_found_def, msg)
            return MethodResult(error=error_value)


class AggregatorIntrospector(ApiProviderIntrospector):
    """
    Specialization of :class:`vmware.vapi.provider.introspection.ApiProviderIntrospector`
    that uses data available in Aggregator Provider to process the Introspection
    service API requests
    """
    def __init__(self, name, local_provider):
        """
        Initialize AggregatorIntrospector

        :type  name: :class:`str`
        :param name: Name of the provider
        :type  local_provider: :class:`vmware.vapi.core.ApiProvider`
        :param local_provider: LocalProvider that will be used to serve
            introspection requests for introspection services itself.
        """
        self._local_provider = local_provider
        self._local_provider_class_name = local_provider.__class__.__name__
        self._service_data = {}
        ApiProviderIntrospector.__init__(self, name)

    def add_service(self, service_id, api_provider):
        """
        Add a new service to the introspector

        :type  service_id: :class:`str`
        :param service_id: Service identifier
        :type  api_provider: :class:`vmware.vapi.core.ApiProvider`
        :param api_provider: ApiProvider that is exposing the service
        """
        self._service_data[service_id] = api_provider

    def remove_service(self, service_id):
        """
        Add a new service to the introspector

        :type  service_id: :class:`str`
        :param service_id: Service identifier
        """
        if service_id in self._service_data:
            del self._service_data[service_id]

    def _get_provider(self, service_id):
        """
        Returns the ApiProvider instance to be used for invoking the
        introspection calls

        :type  service_id: :class:`str`
        :param service_id: Service identifier
        :rtype: :class:`vmware.vapi.core.ApiProvider`
        :return: ApiProvider instance to be used
        """
        #
        # Aggregator routes based on a mapping from Service identifier to
        # ApiProvider. There is an introspection service in the aggregator
        # that is aggregator the data from local provider and all remote
        # providers. So, the mapping in aggregator would be:
        #   com.vmware.vapi.std.introspection.service -> Introspection service
        #       in aggregator
        # But if we route based on this rule, we will go into infinite recursion
        #
        # So, the introspection calls for introspection services should be
        # routed to local provider in the aggregator, as that would be a terminal
        # point and can return data.
        # The introspection data for introspection calls is same if that
        # is serviced by the one in aggregator or by the one in local provider
        #
        if service_id.startswith(Introspection.PACKAGE):
            provider = self._local_provider
        else:
            provider = self._service_data.get(service_id)
        return provider

    def get_checksum(self):
        # XXX: Resultant checksum does not include the data from the services
        # registered in the local provider of the aggregator. Since no one is
        # using Python aggregator, making this a low priority now.
        ctx = ExecutionContext()
        struct_value = StructValue(name=OPERATION_INPUT)
        providers = [provider for provider in list(self._service_data.values())
                     if provider.__class__.__name__ != self._local_provider_class_name]
        method_results = [
            provider.invoke(Introspection.PROVIDER_SVC, 'get', struct_value, ctx)
            for provider in providers]
        checksums = [result.output.get_field('checksum')
                     for result in method_results if result.success()]
        return generate_fingerprint(str(checksums))

    def get_services(self):
        return list(self._service_data.keys())

    def get_service_info(self, service_id):
        provider = self._get_provider(service_id)
        if provider:
            ctx = ExecutionContext()
            struct_value = StructValue(
                name=OPERATION_INPUT,
                values={'id': StringValue(service_id)})
            return provider.invoke(
                Introspection.SERVICE_SVC, 'get',
                struct_value, ctx)
        else:
            msg = message_factory.get_message(
                'vapi.introspection.operation.service.not_found', service_id)
            error_value = make_error_value_from_msgs(not_found_def, msg)
            return MethodResult(error=error_value)

    def get_operations(self, service_id):
        provider = self._get_provider(service_id)
        if provider:
            ctx = ExecutionContext()
            struct_value = StructValue(
                name=OPERATION_INPUT,
                values={'service_id': StringValue(service_id)})
            return provider.invoke(
                Introspection.OPERATION_SVC, 'list',
                struct_value, ctx)
        else:
            msg = message_factory.get_message(
                'vapi.introspection.operation.service.not_found', service_id)
            error_value = make_error_value_from_msgs(not_found_def, msg)
            return MethodResult(error=error_value)

    def get_operation_info(self, service_id, operation_id):
        provider = self._get_provider(service_id)
        if provider:
            ctx = ExecutionContext()
            struct_value = StructValue(
                name=OPERATION_INPUT,
                values={'service_id': StringValue(service_id),
                        'operation_id': StringValue(operation_id)})
            return provider.invoke(
                Introspection.OPERATION_SVC, 'get',
                struct_value, ctx)
        else:
            msg = message_factory.get_message(
                'vapi.introspection.operation.service.not_found', service_id)
            error_value = make_error_value_from_msgs(not_found_def, msg)
            return MethodResult(error=error_value)


def register_instance():
    """
    Services to be registered with LocalProvider

    :rtype: :class:`list` of :class:`vmware.vapi.core.ApiInterface`
    :return: List of services to be registered with LocalProvider
    """
    return [ProviderApiInterface(),
            ServiceApiInterface(),
            OperationApiInterface()]
