"""
API Provider filter
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015, 2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import abc
import six

from vmware.vapi.core import ApiProvider
from vmware.vapi.data.serializers.introspection import (
    convert_data_def_to_data_value)
from vmware.vapi.lib.log import get_vapi_logger
from vmware.vapi.provider.lib import augment_method_result_with_errors

logger = get_vapi_logger(__name__)


@six.add_metaclass(abc.ABCMeta)
class ApiProviderFilter(ApiProvider):
    """
    ApiProviderFilter is a base class for all ApiProvider filters.
    This handles all the common methods and also takes care of augmenting
    errors reported by an ApiProvider filter.

    :type next_provider: :class:`vmware.vapi.core.ApiProvider`
    :ivar next_provider: Next API Provider in the chain
    """
    def __init__(self, next_provider=None, errors_to_augment=None, name=None):
        """
        Initialize ApiProviderFilter

        :type  next_provider: :class:`vmware.vapi.core.ApiProvider` or ``None``
        :param next_provider: API Provider to invoke the requests
        :type  errors_to_augment: :class:`list` of
            :class:`vmware.vapi.data.definition.ErrorDefinition` or ``None``
        :param errors_to_augment: List of error definitions to be added to
            method definitions
        :type  name: :class:`str`
        :param name: The name of the filter
        """
        ApiProvider.__init__(self)
        self.name = name if name is not None else self.__class__.__name__
        self.next_provider = next_provider
        self._error_defs_to_augment = errors_to_augment or []
        self._error_values_to_augment = [
            convert_data_def_to_data_value(error_def)
            for error_def in self._error_defs_to_augment
        ]

    @abc.abstractmethod
    def invoke(self, service_id, operation_id, input_value, ctx):
        """
        Invoke an API request. Derived classes of ApiProviderFilter
        should call this method to invoke the request. This can be done
        by: ApiProviderFilter.invoke(self, ctx, method_id, input_value).

        This method calls the next API Provider. If the request is made to
        "get" operation of vAPI Operation Introspection service, errors are
        augmented to the method result.

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
        method_result = self.next_provider.invoke(
            service_id, operation_id, input_value, ctx)
        return augment_method_result_with_errors(
            service_id, operation_id, method_result,
            self._error_values_to_augment)

    def get_api_provider(self):
        """
        Get the last provider in the chain.

        :rtype: :class:`vmware.vapi.core.ApiProvider`
        :return: Last provider in the provider chain which is not a filter
        """
        if isinstance(self.next_provider, ApiProviderFilter):
            return self.next_provider.get_api_provider()
        return self.next_provider

    def find_first_api_filter(self, name):
        """
        Get the first filter with the specified name in the provider chain

        :type  name: :class:`str`
        :param name: Filter name
        :rtype: :class:`vmware.vapi.core.ApiProviderFilter` or ``None``
        :return: First filter that matches the name
        """
        if self.name == name:
            return self
        if isinstance(self.next_provider, ApiProviderFilter):
            return self.next_provider.find_first_api_filter(name)
        return None
