"""
Interposer API Provider
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015, 2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long


import uuid

from vmware.vapi.core import MethodResult
from vmware.vapi.data.value import StringValue
from vmware.vapi.lib.std import (
    make_std_error_def, make_error_value_from_msg_id)
from vmware.vapi.lib.log import get_vapi_logger
from vmware.vapi.provider.filter import ApiProviderFilter
from vmware.vapi.protocol.client.local_connector import LocalConnector
from vmware.vapi.stdlib.client.introspection import IntrospectableApiProvider


# Configure logging
logger = get_vapi_logger(__name__)

SERVICE_NAME = 'service_name'
OPERATION_NAME = 'operation_name'
OPERATION_INPUT = 'operation_input'


class InterposerType(object):
    """
    Type of all the interposers in vAPI

    :type PRE: :class:`str`
    :ivar PRE: Interposer hook that gets called before each method invocation.
    :type POST: :class:`str`
    :ivar POST: Interposer hook that gets called before each method
                 invocation. If the interposer implementation returns an error,
                 the method invocation is skipped and no further interposer
                 hooks are called for that method invocation.
    :type VETO: :class:`str`
    :ivar VETO: Interposer hook that gets called after each method invocation.
    """
    PRE = 'pre'
    POST = 'post'
    VETO = 'veto'


class NotFound(Exception):
    """
    NotFound is raised when the interposerId is not found in the list
    of registered interposers
    """
    def __init__(self):
        Exception.__init__(self)


class InvalidArgument(Exception):
    """
    InvalidArgument is raised when the argument passed for add a new interposer
    is invalid
    """
    def __init__(self):
        Exception.__init__(self)


class InterposerProvider(ApiProviderFilter):
    """
    InterposerProvider is an interposer implementation of the
    ApiProvider interface. It provides hook in capabilities
    for adding interposers to invoke method calls
    """
    _internal_server_error_def = make_std_error_def(
            'com.vmware.vapi.std.errors.internal_server_error')

    def __init__(self, next_provider=None):
        """
        Initializer InterposerProvider.

        :type  next_provider: :class:`vmware.vapi.core.ApiProvider` or ``None``
        :param next_provider: API Provider to invoke the requests
        """
        ApiProviderFilter.__init__(self, next_provider,
                                   [self._internal_server_error_def])
        # Key: Interposer type, Value: set of interposer ids of that type
        self._interposers = {}

        # Key: Interposer Id, Value: Interposer Map
        self._interposer_map = {}

        # Key: Interposer Id, Value: Method Identifier
        self._interposer_def = {}

        # Method identifiers of all the interposers
        self._interposer_methods = set()

        connector = LocalConnector(self.next_provider)
        self._introspection = IntrospectableApiProvider(connector)

    def invoke(self, service_id, operation_id, input_value, ctx):
        """
        Invoke an API request

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
        try:
            veto_error = self.execute(
                'veto', service_id, operation_id, ctx, input_value)
            if veto_error is not None:
                return MethodResult(error=veto_error)
            else:
                self.execute('pre', service_id, operation_id, ctx, input_value)
                method_result = ApiProviderFilter.invoke(
                    self, service_id, operation_id, input_value, ctx)
                self.execute('post', service_id, operation_id, ctx, input_value)
                return method_result
        except Exception as e:
            logger.exception('service: %s, operation: %s, input_value: %s',
                             service_id, operation_id, input_value)
            error_value = make_error_value_from_msg_id(
                self._internal_server_error_def,
                'vapi.method.invoke.exception',
                str(e))
            method_result = MethodResult(error=error_value)
            return method_result

    def add(self, spec):
        """
        Register a new interposer

        :type  spec:
            :class:`com.vmware.vapi.admin_provider.Interposer.InterposerInfo`
        :param spec: The specification of the interposer. This encapsulates
            details such as the type of the interposer and the list of packages
            that the interposer operates on.
        :rtype: :class:`str`
        :return: ID of the interposer
        :raise: :class:`com.vmware.vapi.std.errors_provider.NotFound`: If
            service name or method name specified in the operation identity
            structure does not exist
        :raise: :class:`vmware.vapi.provider.interposer.InvalidArgument`: If the
            interposer type is invalid
        """
        method_def = self._introspection.get_method(spec.service_name,
                                                    spec.operation_name)
        if spec.type not in [InterposerType.PRE,
                             InterposerType.POST,
                             InterposerType.VETO]:
            raise InvalidArgument()

        interposer_id = str(uuid.uuid4())
        self._interposers.setdefault(spec.type, []).append(interposer_id)
        self._interposer_map[interposer_id] = spec
        self._interposer_methods.add((spec.service_name, spec.operation_name))
        self._interposer_def[interposer_id] = method_def
        return interposer_id

    def get(self, interposer_id):
        """
        Get the information about an interposer

        :type  interposerId: :class:`str`
        :param interposerId: Identifier of the interposer for which the
            information has to be retrieved
        :rtype: :class:`com.vmware.vapi.admin_provider.Interposer.InterposerInfo`
        :return: Information about the interposerId passed in the argument
        :raise: :class:`vmware.vapi.provider.interposer.NotFound`: If the interposer_id does
        """
        info = self._interposer_map.get(interposer_id)
        if info is None:
            raise NotFound()
        else:
            return info

    def list(self):
        """
        List all the registered interposer identifiers

        :rtype: :class:`list` of :class:`str`
        :return: Interposer identifiers
        """
        return sum(list(self._interposers.values()), [])

    def remove(self, interposer_id):
        """
        Unregister an interposer

        :type  interposerId: :class:`str`
        :param interposerId: Identifier of the interposer that has to be
            unregistered
        :raise: :class:`vmware.vapi.provider.interposer.NotFound`: If the interposer_id does
            not exist
        """
        info = self._interposer_map.get(interposer_id)
        if info is None:
            raise NotFound()
        else:
            self._interposers[info.type].remove(interposer_id)
            self._interposer_methods.remove((info.service_name,
                                             info.operation_name))
            del self._interposer_map[interposer_id]

    def _execute_int(self,
                     interposer_id,
                     interposer_type,
                     ctx,
                     service_name,
                     operation_name,
                     opeartion_input):
        """
        Execute an interposer

        :type  interposer_id: :class:`str`
        :param interposer_id: Interposer id
        :type  interposer_type: :class:`InterposerType`
        :param interposer_type: Interposer type
        :type  ctx: :class:`vmware.vapi.core.ExecutionContext`
        :param ctx: Execution context for the invocation
        :type  service_name: :class:`str`
        :param service_name: Name of the service that is being interposed
        :type  operation_name: :class:`str`
        :param operation_name: Name of the operation that is being interposed
        :type  opeartion_input: :class:`vmware.vapi.data.value.DataValue`
        :param opeartion_input: Input for the operation that is being interposed
        :rtype: :class:`vmware.vapi.data.value.ErrorValue`
        :return: Error is returned if the veto interposer execution
                 reported an error, else None
        """
        in_method_def = self._interposer_def.get(interposer_id)
        if in_method_def:
            interposer_input = in_method_def.get_input_definition().new_value()
            interposer_input.set_field(SERVICE_NAME,
                                       StringValue(service_name))
            interposer_input.set_field(OPERATION_NAME,
                                       StringValue(operation_name))
            interposer_input.set_field(OPERATION_INPUT,
                                       opeartion_input)
            in_method_id = in_method_def.get_identifier()
            method_result = ApiProviderFilter.invoke(
                self, in_method_id.get_interface_identifier().get_name(),
                in_method_id.get_name(),
                interposer_input, ctx)

            # Only veto interposers can break the control flow
            if interposer_type == InterposerType.VETO and \
                    not method_result.success():
                return method_result.error

    def execute(self, interposer_type, service_id, operation_id, ctx, input_):
        """
        Execute an interposer

        :type  interposer_type: :class:`InterposerType`
        :param interposer_type: Type of the interposer
        :type  ctx: :class:`vmware.vapi.core.ExecutionContext`
        :param ctx: Execution context for the invocation
        :type  input_: :class:`vmware.vapi.data.value.StructValue`
        :param input_: Input for the method
        :rtype: :class:`vmware.vapi.data.value.ErrorValue`
        :return: Error is returned if the veto interposer execution
                 reported an error, else None
        """
        # Interposers are not allowed to call other interposers
        if (service_id, operation_id) in self._interposer_methods:
            return

        interposer_ids = self._interposers.get(interposer_type)
        if not interposer_ids:
            return

        try:
            for interposer_id in interposer_ids:
                info = self._interposer_map.get(interposer_id)
                pkgs = info.packages
                execute = True if not pkgs else False
                for pkg in pkgs:
                    if service_id.startswith(pkg):
                        execute = True
                if execute:
                    return self._execute_int(interposer_id,
                                             info.type,
                                             ctx,
                                             service_id,
                                             operation_id,
                                             input_)
        except Exception as e:
            logger.error('%s', str(e))


# Single InterposerProvider instance
_interposer_provider = InterposerProvider()


def get_provider():
    """
    Returns the singleton InterposerProvider instance

    :rtype: :class:`InterposerProvider`
    :return: InterposerProvider instance
    """
    return _interposer_provider
