"""
Aggregator Api Provider
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015, 2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long


import requests
import traceback

from vmware.vapi.core import ApiProvider, MethodResult, ExecutionContext
from vmware.vapi.data.value import StructValue
from vmware.vapi.lib import connect
from vmware.vapi.lib.addr_url_parser import get_url_scheme
from vmware.vapi.lib.constants import (Introspection, OPERATION_INPUT)
from vmware.vapi.lib.log import get_vapi_logger
from vmware.vapi.lib.std import make_error_value_from_msgs, make_std_error_def
from vmware.vapi.l10n.runtime import message_factory
from vmware.vapi.provider import local as local_provider
from vmware.vapi.provider.local import LocalProvider
from vmware.vapi.provider.introspection import AggregatorIntrospector


# Configure logging
logger = get_vapi_logger(__name__)


class AggregatorProvider(ApiProvider):
    """
    AggregatorProvider is an aggregating implementation of the
    ApiProvider interface. It aggregates a bunch of ApiProvider
    instances and expose it.
    """
    def __init__(self):
        ApiProvider.__init__(self)
        self._name = 'ApiAggregator'

        # key = service_id, value = api interface
        self._service_id_map = {}

        # key : name, value : provider
        self._providers = {}

        # key : name, value : connection info
        self._provider_data = {}

        # List of all the services present in the local provider
        self._local_service_ids = []

        self._introspection_service_names = [
            Introspection.PROVIDER_SVC,
            Introspection.SERVICE_SVC,
            Introspection.OPERATION_SVC
        ]
        self._introspector = None
        self._authn_chain_processors = []

    _operation_not_found_def = make_std_error_def(
        'com.vmware.vapi.std.errors.operation_not_found')
    _internal_server_error_def = make_std_error_def(
        'com.vmware.vapi.std.errors.internal_server_error')
    _augmented_errors = (_operation_not_found_def,
                         _internal_server_error_def)

    ###########################################################################
    #
    # Support functions for aggregator services
    #
    ###########################################################################

    @staticmethod
    def get_service_identifiers(api_provider):
        """
        Invokes introspection service list on the Api Provider and retrieves
        the list of services

        :type  api_provider: :class:`vmware.vapi.core.ApiProvider`
        :param api_provider: ApiProvider instance to be used for retrieving
            service identifiers
        :rtype: :class:`list` of :class:`str`
        :return: List of service identifiers
        :raise: :class:`Exception`: if service identifiers could not be
            retrieved
        """
        ctx = ExecutionContext()
        service_name = Introspection.SERVICE_SVC
        operation_name = 'list'
        struct_value = StructValue(OPERATION_INPUT)
        method_result = api_provider.invoke(
            service_name, operation_name, struct_value, ctx)
        if method_result.success():
            return [service.value for service in method_result.output]
        else:
            raise Exception('Could not retrieve service identifiers: %s',
                            repr(method_result.error))

    def _process_child(self, provider_cfg, child):
        """
        Process a aggregator child provider_cfg

        :type  provider_cfg: :class:`dict`
        :param provider_cfg: Properties dictionary
        :type  child: :class:`str`
        :param child: Child to be processed
        """
        try:
            url = provider_cfg.get_child_url(child)
            connector = connect.get_requests_connector(
                session=requests.session(), url=url)
            api_provider = connector.get_api_provider()
            rpc_protocol = get_url_scheme(url)
            msg_protocol = provider_cfg.get_provider_message_format(child)
            if api_provider:
                self.register_provider(api_provider,
                                       child,
                                       rpc_protocol,
                                       msg_protocol,
                                       addr=url)
        except Exception as e:
            stack_trace = traceback.format_exc()
            raise Exception('Could not register %s at %s due to %s'
                            % (child, url, stack_trace))

    def register_by_properties(self, provider_cfg):
        """
        Register a provider using a provider_cfg dictionary

        :type  provider_cfg: :class:`dict`
        :param provider_cfg: Properties dictionary
        """
        self._name = provider_cfg.get_provider_name()
        if not self._name:
            self._name = 'ApiAggregator'

        #
        # We have three providers here:
        #   Aggregator: To aggregate services from local and remote providers
        #   IntrospectionProvider: To serve introspection requests. This has
        #       all the introspection services but it will decide whether to
        #       route the introspection call to LocalProvider or Remote provider
        #       based on where it is located.
        #   LocalProvider: To serve requests for services specified in
        #       'local.interfaces'. This also has introspection services that
        #       only provides introspection for services in this LocalProvider.
        #
        # For non-introspection calls:
        # - If service is in LocalProvider, flow is Aggregator -> LocalProvider
        # - If service is in remote ApiProvider, flow is Aggregator -> Remote
        #        api provider
        #
        # For introspection calls:
        # - For a service in remote ApiProvider, flow is
        # Aggregator -> Introspection services in IntrospectionProvider
        # - For a service in LocalProvider, flow is
        # Aggregator -> Introspection services in IntrospectionProvider
        # - For a service in introspection set of services, flow is
        # Aggregator -> IntrospectionProvider -> Introspection services in
        # LocalProvider (If it is handled by IntrospectionProvider, then we
        # will go into infinite recursive calls)
        #

        # Retrieve the local provider singleton instance to hold all the
        # services present in 'local.interfaces' property of in the properties
        # file. Even if there are no interfaces in local.interfaces, this is
        # required as it would serve introspection requests for introspection
        # api.
        l_provider = local_provider.get_provider()
        self._introspector = AggregatorIntrospector(
            self._name, l_provider)
        l_provider.register_by_properties(provider_cfg)

        # Create a local provider to hold the introspection services that
        # aggregates introspection information from the local provider and
        # all the remote providers.
        introspection_provider = LocalProvider(load_introspection=False)
        for service in self._introspector.get_introspection_services():
            # Register the introspection service with the local provider
            introspection_provider.add_interface(service)
            # Register the introspection service with this aggregator
            self.register_service(service.get_identifier().get_name(),
                                  introspection_provider)

        # Registering services from local provider
        service_ids = self.get_service_identifiers(l_provider)
        self._local_service_ids = service_ids
        for service_id in service_ids:
            if service_id not in self._introspection_service_names:
                self.register_service(service_id, l_provider)

        # Register the children
        for child in provider_cfg.get_child_providers():
            self._process_child(provider_cfg, child)

    def get_providers(self):
        """
        Return the connection information of ApiProviders
        registered with the AggregatorProvider

        :rtype: :class:`list` of :class:`tuple` of (
            :class:`str`, :class:`str`, :class:`str`)
        :return: Tuple containing rpc protocol, msg protocol and uri
        """
        return self._provider_data

    def register_service(self, service_id, provider):
        """
        Register an service with the AggregatorProvider

        :type  service_id: :class:`str`
        :param service_id: Service identifier
        :type  provider: :class:`vmware.vapi.core.ApiProvider`
        :param provider: ApiProvider impl. for the specified service identifier
        """
        if service_id in self._service_id_map:
            logger.error('Service already registered: %s', service_id)
        else:
            self._service_id_map[service_id] = provider
            self._introspector.add_service(service_id, provider)
            logger.info('Registering service: %s', service_id)

    def register_provider(self, provider, name, rpc, msg, addr):
        """
        Register a ApiProvider with the AggregatorProvider

        :type  provider: :class:`vmware.vapi.core.ApiProvider`
        :param provider: ApiProvider to be registered
        :type  name: :class:`str`
        :param name: Provider name
        :type  rpc: :class:`str`
        :param rpc: RPC Protocol
        :type  msg: :class:`str`
        :param msg: Msg Protocol
        :type  addr: :class:`str`
        :param addr: URI of the ApiProvider
        """
        self._provider_data[name] = (rpc, msg, addr)
        old_provider = self._providers.get(name)
        if old_provider:
            return

        service_ids = self.get_service_identifiers(provider)
        for service_id in service_ids:
            if service_id not in self._introspection_service_names:
                self.register_service(service_id, provider)
        self._providers[name] = provider

    def unregister_service(self, service_id):
        """
        Unregister an service from AggregatorProvider

        :type  service_id: :class:`str`
        :param service_id: service to be unregistered
        """
        if service_id in self._service_id_map:
            del self._service_id_map[service_id]
            self._introspector.remove_service(service_id)

    def unregister_provider(self, provider_name):
        """
        Unregister a provider from AggregatorProvider

        :type  provider_name: :class:`str`
        :param provider_name: Provider to be unregistered
        """
        provider = self._providers.get(provider_name)
        if not provider:
            return

        service_ids = self.get_service_identifiers(provider)
        for service_id in service_ids:
            self.unregister_service(service_id)
        del self._providers[provider_name]
        del self._provider_data[provider_name]

        logger.info('Unregistering Provider %s',
                    provider.get_definition())

    def unregister_provider_by_name(self, provider_name):
        """
        Unregister a provider from AggregatorProvider

        :type  provider_name: :class:`str`
        :param provider_name: Provider to be unregistered
        """
        self.unregister_provider(provider_name)

    def reload_providers(self):
        """
        Reload all the providers in the AggregatorProvider
        """
        providers = list(self._providers.values()) + [
            local_provider.get_provider()]
        for provider in providers:
            service_ids = self.get_service_identifiers(provider)
            for service_id in service_ids:
                self.register_service(service_id, provider)

    ###########################################################################
    #
    # Implementation of Api Provider interface
    #
    ###########################################################################

    def _invoke_int(self, service_id, operation_id, input_value, ctx):
        """
        Internal implementation of invoke method

        :type  service_id: :class:`str`
        :param service_id: Service identifier
        :type  operation_id: :class:`str`
        :param operation_id: Operation identifier
        :type  input_value: :class:`vmware.vapi.data.value.StructValue`
        :param input_value: Method input parameters
        :type  ctx: :class:`vmware.vapi.core.ExecutionContext`
        :param ctx: Execution context for this method

        :rtype: :class:`vmware.vapi.core.MethodResult`
        :return: Result of the method invocation
        """
        # Check if the provider exists
        provider = self._service_id_map.get(service_id)
        if not provider:
            msg = message_factory.get_message(
                'vapi.method.input.invalid.interface',
                service_id)
            logger.error(msg)
            error_value = make_error_value_from_msgs(
                self._operation_not_found_def, msg)
            return MethodResult(error=error_value)

        # Continue the authentication chain only if the target service
        # is not in the local provider of this process. i.e. for only
        # remote calls
        if service_id not in self._local_service_ids:
            for processor in self._authn_chain_processors:
                ctx.security_context = processor.next_context(
                    ctx.security_context)

        # Actual method execution
        try:
            method_result = provider.invoke(
                service_id, operation_id, input_value, ctx)
            return method_result
        except Exception as e:
            stack_trace = traceback.format_exc()
            logger.error(
                'Service: %s, Operation: %s, input_value %s: exception: %s',
                service_id, operation_id, input_value, stack_trace)
            msg = message_factory.get_message('vapi.method.invoke.exception',
                                              str(e))
            error_value = make_error_value_from_msgs(
                self._internal_server_error_def, msg)
            method_result = MethodResult(error=error_value)
            return method_result

    def invoke(self, service_id, operation_id, input_value, ctx):
        """
        Invokes the specified method using the execution context and
        the input provided

        :type  service_id: :class:`str`
        :param service_id: Service identifier
        :type  operation_id: :class:`str`
        :param operation_id: Operation identifier
        :type  input_value: :class:`vmware.vapi.data.value.StructValue`
        :param input_value: Method input parameters
        :type  ctx: :class:`vmware.vapi.core.ExecutionContext`
        :param ctx: Execution context for this method

        :rtype: :class:`vmware.vapi.core.MethodResult`
        :return: Result of the method invocation
        """
        logger.info("Started: Service: %s, Operation: %s, Ctx: %s",
                    service_id, operation_id, ctx)
        method_result = self._invoke_int(
            service_id, operation_id, input_value, ctx)
        logger.info("Finished: Service: %s. Operation %s, Ctx: %s",
                    service_id, operation_id, ctx)
        return method_result


# Single AggregatorProvider instance
_aggregator_provider = AggregatorProvider()


def get_provider():
    """
    Returns the singleton AggregatorProvider instance

    :rtype: :class:`vmware.vapi.provider.AggregatorProvider`
    :return: AggregatorProvider instance
    """
    return _aggregator_provider
