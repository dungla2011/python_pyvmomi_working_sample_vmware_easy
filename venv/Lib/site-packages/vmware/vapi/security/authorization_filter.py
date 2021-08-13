"""
Authorization API Provider filter
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015, 2017-2019 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import json
import six

from vmware.vapi.core import MethodResult
from vmware.vapi.lib.constants import AUTHN_IDENTITY
from vmware.vapi.lib.log import get_vapi_logger
from vmware.vapi.lib.std import (
    make_std_error_def, make_error_value_from_msg_id)
from vmware.vapi.provider.filter import ApiProviderFilter
from vmware.vapi.security.authentication_filter import NO_AUTH

# Configure logging
logger = get_vapi_logger(__name__)


def get_metadata(metadata_files):
    """
    Get the metadata from the json files

    :type  metadata_files: :class:`list` of `str`
    :param metadata_files: List of authentication metadata files
    :rtype: :class:`dict` or :class:`None`
    :return: Authorization metadata
    """
    if metadata_files:
        metadata = None
        component_data = {}
        for metadata_file in metadata_files:
            with open(metadata_file, 'r') as fp:
                metadata = fp.read()
            authn_metadata = json.loads(metadata).get('authentication', {})  # pylint: disable=E1103
            tmp_component_data = authn_metadata.get('component', {})
            if not tmp_component_data:
                tmp_component_data = authn_metadata.get('product', {})

            component_name = tmp_component_data.get('name')
            for key, val in tmp_component_data.items():
                if key == 'schemes':
                    # Prefix every scheme name with component name
                    value = {'%s:%s' % (component_name, k): v
                             for k, v in val.items()}
                elif key in ['operations', 'services', 'packages']:
                    # Prefix every scheme name for packages, services and
                    # operations with component name
                    component_value = {}
                    for k, v in val.items():
                        if not isinstance(v, list):
                            v = [v]
                        component_value.setdefault(k, []).extend(
                            ['%s:%s' % (component_name, value) for value in v])
                    value = component_value
                else:
                    value = val

                if isinstance(value, dict):
                    component_data.setdefault(key, {}).update(value)
                else:
                    component_data[key] = value
        return component_data
    return None


class AuthorizationFilter(ApiProviderFilter):
    """
    AuthorizationFilter in API Provider chain enforces the authorization
    schemes specified in the authorization metadata file
    """
    def __init__(self, next_provider=None, provider_config=None):
        """
        Initialize AuthorizationFilter

        :type  next_provider: :class:`vmware.vapi.core.ApiProvider`
        :param next_provider: API Provider to invoke the requests
        :type  provider_config:
            :class:`vmware.vapi.settings.config.ProviderConfig` or :class:`None`
        :param provider_config: Provider configuration object
        """
        handler_names = []
        self._metadata = None
        self._task_authz_handler = None
        from vmware.vapi.lib.load import dynamic_import

        if provider_config:
            # Get the registered AuthN handlers from config file
            (handler_names, metadata_files) = \
                provider_config.get_authorization_handlers_and_files()
            self._metadata = get_metadata(metadata_files)

            # If tasks are enabled add Tasks Authz Handler as well
            if provider_config.are_tasks_enabled():
                handler_constructor = dynamic_import(
                    'com.vmware.vapi.task.tasks_impl.TasksAuthzHandler')
                self._task_authz_handler = handler_constructor()

        self._authz_handlers = []
        for handler_name in handler_names:
            # Dynamically load the AuthZ handler
            handler_constructor = dynamic_import(handler_name)
            if handler_constructor is None:
                raise ImportError('Could not import %s' % handler_name)

            self._authz_handlers.append(handler_constructor())

        self._internal_server_error_def = make_std_error_def(
            'com.vmware.vapi.std.errors.internal_server_error')
        self._unauthorized_error_def = make_std_error_def(
            'com.vmware.vapi.std.errors.unauthorized')
        ApiProviderFilter.__init__(self, next_provider,
                                   [self._internal_server_error_def,
                                    self._unauthorized_error_def])

    def _get_scheme(self, scheme_rules, key):
        """
        Extract the scheme identifier

        :type  scheme_rules: :class:`dict`
        :param scheme_rules: Scheme rules
        :type  key: :class:`str`
        :param key: Key to retrieve the scheme name from scheme rules
        :rtype: :class:`str`
        :return: Scheme identifier
        """
        try:
            scheme_ids = []
            scheme_names = scheme_rules[key]
            if len(scheme_names) and not isinstance(scheme_names, list):
                scheme_names = [scheme_names]
            if scheme_names:
                # Scheme name is present, get the scheme id
                scheme_data = self._metadata.get('schemes')
                for scheme_name in scheme_names:
                    scheme_info = scheme_data.get(scheme_name)
                    if scheme_info is None:
                        # Scheme info is not present
                        raise ValueError(scheme_name)
                    else:
                        scheme_id = scheme_info.get('authenticationScheme')
                        scheme_ids.append(scheme_id)
            else:
                # Scheme rule is present but there is no authn scheme
                scheme_ids.append(NO_AUTH)
            return scheme_ids
        except KeyError:
            pass

    def _get_package_specific_scheme(self, service_id, operation_id):  # pylint: disable=W0613
        """
        Get the package specific scheme for the input operation

        :type  service_id: :class:`str`
        :param service_id: Service identifier
        :type  operation_id: :class:`str`
        :param operation_id: Operation identifier
        :rtype: :class:`str`
        :return: Authentication scheme identifier
        """
        package_data = self._metadata.get('packages')
        package_name = service_id.rsplit('.', 1)[0]
        packages_match = [package for package in six.iterkeys(package_data)
                          if package_name.startswith(package)]
        if packages_match:
            closest_package = max(packages_match, key=len)
            return self._get_scheme(package_data, closest_package)
        return None

    def _get_service_specific_scheme(self, service_id, operation_id):  # pylint: disable=W0613
        """
        Get the service specific scheme for the input operation

        :type  service_id: :class:`str`
        :param service_id: Service identifier
        :type  operation_id: :class:`str`
        :param operation_id: Operation identifier
        :rtype: :class:`str`
        :return: Authentication scheme identifier
        """
        service_data = self._metadata.get('services')
        return self._get_scheme(service_data,
                                '%s' % service_id)

    def _get_operation_specific_scheme(self, service_id, operation_id):
        """
        Get the operation specific scheme for the input operation

        :type  service_id: :class:`str`
        :param service_id: Service identifier
        :type  operation_id: :class:`str`
        :param operation_id: Operation identifier
        :rtype: :class:`str`
        :return: Authentication scheme identifier
        """
        operation_data = self._metadata.get('operations')
        return self._get_scheme(operation_data,
                                '%s.%s' % (service_id, operation_id))

    def _allowed_schemes(self, service_id, operation_id):
        """
        Get the effective list of authentication schemes supported
        by the operation

        :type  service_id: :class:`str`
        :param service_id: Service identifier
        :type  operation_id: :class:`str`
        :param operation_id: Operation identifier
        :rtype: :class:`list` of `str`
        :return: List of supported authentication schemes
        """
        schemes = None
        for scheme_fn in [self._get_operation_specific_scheme,
                          self._get_service_specific_scheme,
                          self._get_package_specific_scheme]:
            schemes = scheme_fn(service_id, operation_id)
            if schemes:
                break

        return schemes

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
        authn_result = sec_ctx.get(AUTHN_IDENTITY)

        try:
            allowed_authn_schemes = self._allowed_schemes(
                service_id, operation_id)
        except Exception:
            logger.exception(
                'Cannot parse authentication metadata for operation %s of service %s: %s',
                operation_id,
                service_id,
                e)
            error_value = make_error_value_from_msg_id(
                self._internal_server_error_def,
                'vapi.security.authentication.metadata.invalid', operation_id,
                service_id)
            return MethodResult(error=error_value)

        if allowed_authn_schemes is None or NO_AUTH in allowed_authn_schemes:
            is_no_auth_allowed = True
        else:
            is_no_auth_allowed = False

        # No valid AuthN info received from AuthN filter for an
        # operation which requires authentication
        if (authn_result is None and not is_no_auth_allowed):
            error_value = make_error_value_from_msg_id(
                self._unauthorized_error_def,
                'vapi.security.authorization.invalid')
            return MethodResult(error=error_value)

        if service_id == 'com.vmware.cis.tasks'\
                and self._task_authz_handler is not None:
            result = self._task_authz_handler.authorize(service_id,
                                                        operation_id,
                                                        input_value,
                                                        sec_ctx)

            if not result:
                error_value = make_error_value_from_msg_id(
                    self._unauthorized_error_def,
                    'vapi.security.authorization.invalid')
                return MethodResult(error=error_value)

        if is_no_auth_allowed:
            return ApiProviderFilter.invoke(
                self, service_id, operation_id, input_value, ctx)
        else:
            result = None
            for handler in self._authz_handlers:
                # Call authorize method and validate authZ info
                try:
                    result = handler.authorize(
                        service_id, operation_id, sec_ctx)
                except Exception as e:
                    logger.exception(
                        'Error in invoking authorization handler %s - %s',
                        handler, e)
                    error_value = make_error_value_from_msg_id(
                        self._internal_server_error_def,
                        'vapi.security.authorization.exception',
                        str(e))
                    return MethodResult(error=error_value)

                if result:
                    return ApiProviderFilter.invoke(
                        self, service_id, operation_id, input_value, ctx)

            error_value = make_error_value_from_msg_id(
                self._unauthorized_error_def,
                'vapi.security.authorization.invalid')
            return MethodResult(error=error_value)


# Single AuthorizationFilter instance
_authz_filter = AuthorizationFilter()


def get_provider():
    """
    Returns the singleton AuthorizationFilter instance

    :rtype:
        :class:`vmware.vapi.security.authorization_filter.AuthorizationFilter`
    :return: AuthorizationFilter instance
    """
    return _authz_filter
