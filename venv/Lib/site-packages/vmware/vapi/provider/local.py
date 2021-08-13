"""
Local Api Provider
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015-2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import inspect
import traceback

from vmware.vapi.core import (
    ApiInterface, ApiProvider, MethodResult, MethodIdentifier,
    InterfaceIdentifier)
from vmware.vapi.data.definition import (
    DataDefinition,
    StructDefinition
)
from vmware.vapi.data.type import Type
from vmware.vapi.lib.std import (
    make_error_value_from_error_value_and_msgs,
    make_error_value_from_msg_id,
    make_error_value_from_msgs,
    make_std_error_def,
)
from vmware.vapi.data.serializers.introspection import (
    convert_data_def_to_data_value)
from vmware.vapi.l10n.runtime import message_factory
from vmware.vapi.lib.log import get_vapi_logger
from vmware.vapi.bindings.skeleton import VapiInterface
from vmware.vapi.provider import introspection
from vmware.vapi.provider.lib import augment_method_result_with_errors

logger = get_vapi_logger(__name__)


class LocalProvider(ApiProvider):
    """
    LocalProvider is a local in-process implementation of the
    ApiProvider interface
    """
    # XXX These error definitions should be eliminated when we figure out
    #     where/how to get the error definitions used by the local provider
    _internal_server_error_def = make_std_error_def(
        'com.vmware.vapi.std.errors.internal_server_error')
    _invalid_argument_def = make_std_error_def(
        'com.vmware.vapi.std.errors.invalid_argument')
    _operation_not_found_def = make_std_error_def(
        'com.vmware.vapi.std.errors.operation_not_found')

    def __init__(self, load_introspection=True):
        """
        Initialize LocalProvider

        :type  load_introspection: :class:`bool`
        :param load_introspection: If true, load introspection services
        """
        ApiProvider.__init__(self)
        self._name = "LocalProvider"
        # key = service id, value = api interface
        self._service_map = {}

        self._introspector = introspection.LocalProviderIntrospector(self._name)
        if load_introspection:
            self.add_interface(
                self._introspector.get_introspection_services())

        self._error_defs_to_augment = [
            self._internal_server_error_def,
            self._invalid_argument_def,
            self._operation_not_found_def,
        ]
        # these are the errors that should be augmented
        # when `get` operation is invoked on
        # com.vmware.vapi.std.introspection.Operation
        self._error_values_to_augment = [
            convert_data_def_to_data_value(error_def)
            for error_def in self._error_defs_to_augment
        ]

    def register_by_properties(self, provider_cfg):
        """
        Register set of interfaces using provider configuration object

        :type  provider_cfg: :class:`vmware.vapi.settings.config.ProviderConfig`
        :param provider_cfg: Configuration for this vAPI provider
        """
        self._name = provider_cfg.get_provider_name()

        services = provider_cfg.get_interfaces()
        for service in services:
            service = service.strip()
            if service:

                # Get the service specific configuration from the config
                service_cfg = provider_cfg.get_service_config(service)

                fn = "register_instance"
                try:
                    module = __import__(service, globals(), locals(), [fn])
                    register_fn = getattr(module, fn)

                    # XXX: Remove the if condition once all the implementations
                    # have been updated to use the new cfg parameter
                    if inspect.getargspec(register_fn).args:  # pylint: disable=W1505
                        ifaces = register_fn(service_cfg)
                    else:
                        ifaces = register_fn()
                    self.add_interface(ifaces)
                except Exception:
                    stack_trace = traceback.format_exc()
                    raise Exception('Could not add service %s due to %s'
                                    % (service, stack_trace))

    def add_interface(self, ifaces):
        """
        Register an interface with LocalProvider

        :type  ifaces: :class:`list` of :class:`vmware.vapi.core.ApiInterface`
        :param ifaces: Interfaces to be registered
        """
        if not isinstance(ifaces, list):
            ifaces = [ifaces]

        for iface in ifaces:
            # iface could be VapiInterface if bindings layer is registering
            # it's interfaces. In that case, extract the skeleton from
            # VapiInterface
            if isinstance(iface, VapiInterface):
                api_iface = iface.api_interface
            # In Dynamic providers, where ApiInterface is implemented directly
            # instead of using bindings, an instance of ApiInterface is passed
            elif isinstance(iface, ApiInterface):
                api_iface = iface
            else:
                raise Exception(
                    'Could not register the interface %s. It has to be either '
                    'an instance of vmware.vapi.bindings.VapiInterface or '
                    'an instance of vmware.vapi.core.ApiInterface' %
                    str(iface.__class__))

            service_id = api_iface.get_identifier().get_name()
            if service_id in self._service_map:
                raise Exception('Service already registered: %s' % service_id)

            logger.info('Registering service: %s', service_id)
            self._service_map[service_id] = api_iface
            if self._introspector:
                self._introspector.add_service(service_id, api_iface)

    @staticmethod
    def _validate_error(error_value, method_definition):
        """
        Validate the error_value is allowed to be reported by the method
        described by method_definition.

        :type  error_value: :class:`vmware.vapi.data.value.ErrorValue`
        :param error_value: Error value to validate
        :type  method_definition: :class:`vmware.vapi.core.MethodDefinition`
        :param method_definition: definition of the method to validate against.
        :rtype: :class:`vmware.vapi.message.Message` or None
        :return: the messages describing the validation failure or None if
                 validation succeeded
        """

        error_def = method_definition.get_error_definition(error_value.name)
        if error_def is None:
            method_id = method_definition.get_identifier()
            logger.error("Method %s reported the error %s which is not in "
                         "MethodDefinition",
                         method_id.get_name(), error_value.name)
            message = message_factory.get_message(
                    'vapi.method.status.errors.invalid',
                    error_value.name, str(method_id.get_name()))
            return [message]
        messages = error_def.validate(error_value)
        return messages

    def _invoke_int(self, service_id, operation_id, input_value, ctx):  # pylint: disable=R0911
        """
        Internal implementation of InvokeMethod

        :type  service_id: :class:`str`
        :param service_id: Service identifier
        :type  operation_id: :class:`str`
        :param operation_id: Operation identifier
        :type  ctx: :class:`vmware.vapi.core.ExecutionContext`
        :param ctx: Execution context for this method
        :type  input_value: :class:`vmware.vapi.data.value.StructValue`
        :param input_value: Method input parameters

        :rtype: :class:`vmware.vapi.core.MethodResult`
        :return: Result of the method invocation
        """
        # Step 0: Verify input types
        if (input_value and not (input_value.type == Type.STRUCTURE)):
            logger.error("Invalid inputs")
            error_value = make_error_value_from_msg_id(
                self._invalid_argument_def, 'vapi.method.input.invalid')
            return MethodResult(error=error_value)

        iface_id = InterfaceIdentifier(service_id)
        method_id = MethodIdentifier(iface_id, operation_id)

        # Step 1: Get method definition
        iface = self._service_map.get(service_id)
        if not iface:
            logger.error('Could not find service: %s', service_id)
            error_value = make_error_value_from_msg_id(
                self._operation_not_found_def,
                'vapi.method.input.invalid.interface',
                service_id)
            return  MethodResult(error=error_value)

        method_def = iface.get_method_definition(method_id)
        if not method_def:
            logger.error("Could not find method %s", method_id.get_name())
            error_value = make_error_value_from_msg_id(
                self._operation_not_found_def,
                'vapi.method.input.invalid.method',
                method_id.get_name())
            return MethodResult(error=error_value)

        input_def = method_def.get_input_definition()
        if not isinstance(input_def, StructDefinition):
            error_value = make_error_value_from_msg_id(
                self._internal_server_error_def,
                'vapi.method.input.invalid.definition')
            return MethodResult(error=error_value)

        output_def = method_def.get_output_definition()
        if not isinstance(output_def, DataDefinition):
            error_value = make_error_value_from_msg_id(
                self._internal_server_error_def,
                'vapi.method.output.invalid.definition')
            return MethodResult(error=error_value)

        # Step 2: Validate input with input def
        input_def.complete_value(input_value)
        messages = input_def.validate(input_value)
        if messages:
            logger.error("Input validation failed for method %s",
                         method_id.get_name())
            error_value = make_error_value_from_msgs(
                self._invalid_argument_def, *messages)
            return MethodResult(error=error_value)

        # Step 3: Execute method
        method_result = iface.invoke(ctx, method_id, input_value)

        # Step 4: Validate output with output def or error against errors set
        if method_result.success():
            messages = output_def.validate(method_result.output)
            if messages:
                logger.error("Output validation failed for method %s",
                             method_id.get_name())
                error_value = make_error_value_from_msgs(
                    self._internal_server_error_def, *messages)
                return MethodResult(error=error_value)
        else:
            error_value = method_result.error
            messages = self._validate_error(error_value, method_def)
            if messages:
                new_error_value = make_error_value_from_error_value_and_msgs(
                    self._internal_server_error_def,
                    error_value,
                    *messages)
                return MethodResult(error=new_error_value)

        return method_result

    def invoke(self, service_id, operation_id, input_value, ctx):
        logger.debug(
            'Operation started: Service: %s, Operation: %s, Ctx: %s, Input: %s',
            service_id, operation_id, ctx, input_value)
        try:
            method_result = self._invoke_int(
                service_id, operation_id, input_value, ctx)
            if method_result.success():
                method_result = augment_method_result_with_errors(
                    service_id,
                    operation_id,
                    method_result,
                    self._error_values_to_augment)
        except Exception as e:
            logger.exception("Error in invoking %s in %s - %s",
                             service_id, operation_id, e)
            error_value = make_error_value_from_msg_id(
                self._internal_server_error_def,
                'vapi.method.invoke.exception',
                str(e))
            method_result = MethodResult(error=error_value)
        logger.debug(
            'Operation finished: Service: %s, Operation %s, Ctx: %s, '
            'Output: %s',
            service_id, operation_id, ctx, method_result)
        return method_result


# Singleton LocalProvider instance
_local_provider = LocalProvider()


def get_provider():
    """
    Returns the singleton LocalProvider instance

    :rtype: :class:`LocalProvider`
    :return: LocalProvider instance
    """
    return _local_provider
