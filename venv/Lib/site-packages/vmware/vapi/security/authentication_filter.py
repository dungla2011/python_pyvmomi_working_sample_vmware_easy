"""
Authentication API Provider filter
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015, 2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

from vmware.vapi.core import ExecutionContext, MethodResult, SecurityContext
from vmware.vapi.lib.constants import AUTHN_IDENTITY, SCHEME_ID
from vmware.vapi.lib.log import get_vapi_logger
from vmware.vapi.lib.std import make_std_error_def, make_error_value_from_msg_id
from vmware.vapi.provider.filter import ApiProviderFilter


# Configure logging
logger = get_vapi_logger(__name__)
NO_AUTH = 'com.vmware.vapi.std.security.no_authentication'


class AuthenticationFilter(ApiProviderFilter):
    """
    AuthenticationFilter in API Provider chain enforces the authentication
    schemes specified in the authentication metadata file
    """
    def __init__(self, next_provider=None, provider_config=None):
        """
        Initialize AuthenticationFilter

        :type  next_provider: :class:`vmware.vapi.core.ApiProvider`
        :param next_provider: API Provider to invoke the requests
        :type  provider_config:
            :class:`vmware.vapi.settings.config.ProviderConfig` or :class:`None`
        :param provider_config: Provider configuration object
        """
        # Get the registered AuthN handlers from the config file
        handler_names = provider_config.get_authentication_handlers() \
            if provider_config else []
        self._authn_handlers = []

        from vmware.vapi.lib.load import dynamic_import
        for handler_name in handler_names:
            # Dynamically load the AuthN handler
            handler_constructor = dynamic_import(handler_name)
            if handler_constructor is None:
                raise ImportError('Could not import %s' % handler_name)

            self._authn_handlers.append(handler_constructor())

        self._internal_server_error_def = make_std_error_def(
            'com.vmware.vapi.std.errors.internal_server_error')
        self._unauthenticated_error_def = make_std_error_def(
            'com.vmware.vapi.std.errors.unauthenticated')
        ApiProviderFilter.__init__(self, next_provider,
                                   [self._internal_server_error_def,
                                    self._unauthenticated_error_def])

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
        sec_ctx = ctx.security_context
        app_ctx = ctx.application_context
        authn_result = None

        request_scheme = sec_ctx.get(SCHEME_ID)
        if (self._authn_handlers and request_scheme
                and request_scheme != NO_AUTH):
            for handler in self._authn_handlers:
                # Call authenticate method and get the UserIdentity
                try:
                    authn_result = handler.authenticate(sec_ctx)
                except Exception as e:
                    logger.exception(
                        'Error in invoking authentication handler %s - %s',
                        handler, e)
                    error_value = make_error_value_from_msg_id(
                        self._internal_server_error_def,
                        'vapi.security.authentication.exception',
                        str(e))
                    return MethodResult(error=error_value)

                # authn result false means authentication failed
                if authn_result is False:
                    error_value = make_error_value_from_msg_id(
                        self._unauthenticated_error_def,
                        'vapi.security.authentication.invalid')
                    return MethodResult(error=error_value)

                if authn_result is not None:
                    # Matching authN handler found
                    break

        if authn_result:
            # Add the authN identity to the security context to pass on to next
            # provider
            sec_ctx[AUTHN_IDENTITY] = authn_result
            ctx = ExecutionContext(app_ctx, sec_ctx)
        else:
            # No AuthN handler found pass an empty security context
            ctx = ExecutionContext(app_ctx, SecurityContext())

        return ApiProviderFilter.invoke(
            self, service_id, operation_id, input_value, ctx)

# Single AuthenticationFilter instance
_authn_filter = AuthenticationFilter()


def get_provider():
    """
    Returns the singleton AuthenticationFilter instance

    :rtype:
        :class:`vmware.vapi.security.authentication_filter.AuthenticationFilter`
    :return: AuthenticationFilter instance
    """
    return _authn_filter
