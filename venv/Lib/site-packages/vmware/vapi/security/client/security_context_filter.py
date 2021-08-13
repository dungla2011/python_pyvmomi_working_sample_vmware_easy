"""
SecurityContext API Provider filter
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2017, 2019 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import abc
import six

from vmware.vapi.core import ExecutionContext
from vmware.vapi.lib.log import get_vapi_logger
from vmware.vapi.provider.filter import ApiProviderFilter


# Configure logging
logger = get_vapi_logger(__name__)


@six.add_metaclass(abc.ABCMeta)
class SecurityContextFilter(ApiProviderFilter):
    """
    SecurityContextFilter in API Provider chain adds the security
    context to the execution context passed in.
    """
    def __init__(self, next_provider=None):
        """
        Initialize SecurityContextFilter

        :type  next_provider: :class:`vmware.vapi.core.ApiProvider`
        :param next_provider: API Provider to invoke the requests
        """
        ApiProviderFilter.__init__(self, next_provider)

    @abc.abstractmethod
    def get_max_retries(self):
        """
        Get the max number of retries

        :rtype: :class:`int`
        :return: Number of retries
        """

    @abc.abstractmethod
    def get_security_context(self, on_error):
        """
        Retrieve security context. If this method is called after an error
        occured and the request needs to be retried, then a new security context
        may be created depending on the scheme.

        :type  on_error: :class:`bool`
        :param on_error: Whether this method is called after getting an error
        :rtype: :class:`vmware.vapi.core.SecurityContext`
        :return: Security context
        """

    @abc.abstractmethod
    def should_retry(self, error_value):
        """
        Returns whether the request should be retried or not based on the error.

        :type  error_value: :class:`vmware.vapi.data.value.ErrorValue`
        :param error_value: Method error
        :rtype: :class:`bool`
        :return: Returns True if request should be retried based on the error
            value provided else False
        """

    def invoke(self, service_id, operation_id, input_value, ctx):   # pylint: disable=R1710
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
        app_ctx = ctx.application_context if ctx else None
        on_error = False
        for i in range(0, self.get_max_retries() + 1):
            # Typically get_security_context() should always return a valid
            # security context. In case of LegacySecurityContextFilter,
            # get_security_context() may return None if no security context is
            # set and hence needs to be handled.
            sec_ctx = (self.get_security_context(on_error)
                       or (ctx.security_context if ctx else None))
            # Reuse the exist ExecutionContext object if present
            # ExecutionContext object may contain more fields
            if ctx is not None:
                ctx.application_context = app_ctx
                ctx.security_context = sec_ctx
            else:
                ctx = ExecutionContext(app_ctx, sec_ctx)
            method_result = ApiProviderFilter.invoke(
                self, service_id, operation_id, input_value, ctx)
            if (method_result.error is None
                    or not self.should_retry(method_result.error)):
                return method_result
            on_error = True


class LegacySecurityContextFilter(SecurityContextFilter):
    """
    SecurityContextFilter in API Provider chain adds the security
    context to the execution context passed in.
    """
    def __init__(self, next_provider=None, security_context=None):
        """
        Initialize SecurityContextFilter

        :type  next_provider: :class:`vmware.vapi.core.ApiProvider`
        :param next_provider: API Provider to invoke the requests
        :type  security_context: :class:`vmware.vapi.core.SecurityContext`
        :param security_context: Security context
        """
        SecurityContextFilter.__init__(self, next_provider)
        self._security_context = security_context

    def get_max_retries(self):
        """
        Get the max number of retries

        :rtype: :class:`int`
        :return: Number of retries
        """
        return 0

    def set_security_context(self, security_context):
        """
        Set security context

        :type  security_context: :class:`vmware.vapi.core.SecurityContext`
        :param security_context: Security context
        """
        self._security_context = security_context

    def get_security_context(self, on_error):
        """
        Retrieve the stored security context.

        :type  on_error: :class:`bool`
        :param on_error: Whether this method is called after getting an error
        :rtype: :class:`vmware.vapi.core.SecurityContext` or ``None``
        :return: Security context or None
        """
        # This method shouldn't return None but it is violating in cases when no
        # security context is set
        return self._security_context

    def should_retry(self, error_value):
        """
        Returns whether the request should be retried or not based on the error.

        :type  error_value: :class:`vmware.vapi.data.value.ErrorValue`
        :param error_value: Method error
        :rtype: :class:`bool`
        :return: Returns True if request should be retried based on the error
            value provided else False
        """
        return False
