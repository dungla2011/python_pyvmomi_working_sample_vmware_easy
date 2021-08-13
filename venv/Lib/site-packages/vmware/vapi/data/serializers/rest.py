"""
REST de/serializer
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2017-2018 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import base64
import six

from vmware.vapi.core import MethodResult
from vmware.vapi.data.value import (
    BooleanValue, ErrorValue, IntegerValue, ListValue, OptionalValue,
    StringValue, StructValue, VoidValue)
from vmware.vapi.exception import CoreException
from vmware.vapi.lib.constants import SCHEME_ID
from vmware.vapi.lib.log import get_vapi_logger
from vmware.vapi.l10n.runtime import message_factory
from vmware.vapi.rest.lib import http_to_vapi_error_map, successful_status_codes
from vmware.vapi.security.oauth import ACCESS_TOKEN, OAUTH_SCHEME_ID
from vmware.vapi.security.session import (
    REST_SESSION_ID_KEY, SESSION_ID, SESSION_SCHEME_ID)
from vmware.vapi.security.user_password import (
    PASSWORD_KEY, USER_KEY, USER_PASSWORD_SCHEME_ID)

from .cleanjson import DataValueConverter

logger = get_vapi_logger(__name__)


class RequestSerializer(object):
    """ REST request serializer """
    @staticmethod
    def serialize_request(input_value, ctx, rest_metadata, is_vapi_rest):
        """
        Serialize the request as a REST request

        :type  input_value: :class:`vmware.vapi.data.value.StructValue`
        :param input_value: method input parameters
        :type  ctx: :class:`vmware.vapi.core.ExecutionContext`
        :param ctx: execution context object
        :type  rest_metadata:
            :class:`vmware.vapi.lib.rest.OperationRestMetadata`
        :param rest_metadata: Rest request metadata
        :type  is_vapi_rest: :class:`bool`
        :param is_vapi_rest: Whether the Rest json message format is VAPI Rest
            or not
        :rtype   :class:`tuple`
        :return: Tuple of URL path, HTTP headers, request body and cookies
        """
        # Serialize request and return (headers, body)
        url_path, input_headers, request_body_str = \
            RequestSerializer.serialize_input(input_value, rest_metadata)
        sec_ctx = ctx.security_context if ctx is not None else None
        # TODO add support for application context
        authz_headers, cookies = RequestSerializer.get_authorization_headers(
            sec_ctx, is_vapi_rest)
        # Concatenate all headers
        all_headers = input_headers
        all_headers.update(authz_headers)
        if rest_metadata is not None:
            dispatch_headers = rest_metadata.get_dispatch_header()
        else:
            dispatch_headers = {}
        all_headers.update(dispatch_headers)
        return (url_path, all_headers, request_body_str, cookies)

    @staticmethod
    def serialize_input(input_value, rest_metadata):
        """
        Serialize the input value

        :type  input_value: :class:`vmware.vapi.data.value.StructValue`
        :param input_value: method input parameters
        :type  rest_metadata:
            :class:`vmware.vapi.lib.rest.OperationRestMetadata`
        :param rest_metadata: Rest request metadata
        :rtype   :class:`tuple`
        :return: Tuple of URL path, HTTP headers and request body
        """
        if rest_metadata is not None:
            path_variable_field_names = \
                rest_metadata.get_path_variable_field_names()
            query_param_field_names = \
                rest_metadata.get_query_parameter_field_names()
            header_field_names = \
                rest_metadata.get_header_field_names()
            request_body_param = rest_metadata.request_body_parameter
        else:
            path_variable_field_names = []
            query_param_field_names = []
            header_field_names = []
            request_body_param = None
        if request_body_param is not None:
            request_body_input_value = input_value.get_field(request_body_param)
        else:
            request_body_input_value = StructValue(name=input_value.name)
        path_variable_fields = {}
        query_param_fields = {}
        header_fields = {}
        for (field_name, field_val) in input_value.get_fields():
            if field_name in path_variable_field_names:
                field_str = RequestSerializer._convert_to_string(field_val)
                if field_str is not None:
                    path_variable_fields[field_name] = field_str
            elif field_name in query_param_field_names:
                field_str = RequestSerializer._convert_to_string(field_val)
                if field_str is not None:
                    query_param_fields[field_name] = field_str
            elif field_name in header_field_names:
                field_str = RequestSerializer._convert_to_string(field_val)
                if field_str is not None:
                    header_fields[field_name] = field_str
            elif request_body_param is None:
                request_body_input_value.set_field(field_name, field_val)
        url_path = rest_metadata.get_url_path(
            path_variable_fields, query_param_fields) if rest_metadata else None
        return (url_path, header_fields,
                DataValueConverter.convert_to_json(request_body_input_value))

    @staticmethod
    def _convert_to_string(data_value):
        """
        Serialize data value to string for use in Request URL

        :type  data_value: :class:`vmware.vapi.data.value.DataValue`
        :param data_value: Data value
        :rtype   :class:`str` or :class:`NoneType`
        :return: Serialized string for use in Request URL or None
        """
        if isinstance(data_value, OptionalValue):
            if data_value.is_set():
                return RequestSerializer._convert_to_string(data_value.value)
            else:
                return None
        elif isinstance(data_value, BooleanValue):
            return DataValueConverter.convert_to_json(data_value)
        elif isinstance(data_value, StringValue):
            return data_value.value
        elif isinstance(data_value, IntegerValue):
            return str(data_value.value)
        else:
            msg = message_factory.get_message(
                'vapi.data.serializers.rest.unsupported_data_value',
                data_value.type)
            raise CoreException(msg)

    @staticmethod
    def get_authorization_headers(security_context, is_vapi_rest):
        """
        Get the authorization headers for the corresponding security context

        :type  security_context: :class:`vmware.vapi.core.SecurityContext`
        :param security_context: Security context
        :type  is_vapi_rest: :class:`bool`
        :param is_vapi_rest: Whether the Rest json message format is VAPI Rest
            or not
        :rtype   :class:`tuple`
        :return: Tuple of HTTP headers and cookies
        """
        if security_context is None:
            return ({}, None)
        # TODO Add other schemes (SAML)
        if security_context.get(SCHEME_ID) == USER_PASSWORD_SCHEME_ID:
            return RequestSerializer._visit_username_security_context(
                security_context)
        elif security_context.get(SCHEME_ID) == SESSION_SCHEME_ID:
            return RequestSerializer._visit_session_security_context(
                security_context, is_vapi_rest)
        elif security_context.get(SCHEME_ID) == OAUTH_SCHEME_ID:
            return RequestSerializer._visit_oauth_security_context(
                security_context, is_vapi_rest)
        else:
            return ({}, None)

    @staticmethod
    def _visit_username_security_context(security_context):
        """
        Get the authorization headers for username security context

        :type  security_context: :class:`vmware.vapi.core.SecurityContext`
        :param security_context: Security context
        :rtype   :class:`tuple`
        :return: Tuple of HTTP headers and cookies
        """
        username = security_context.get(USER_KEY)
        password = security_context.get(PASSWORD_KEY)
        credential_string = '%s:%s' % (username, password)
        if six.PY2:
            authorization_val = ' '.join(['Basic',
                                          base64.b64encode(credential_string)])
        else:
            # b64encode expects a bytes-like object and in Python 3, default is
            # unicode
            credential_string = credential_string.encode('utf-8')
            authorization_val = b' '.join([b'Basic',
                                           base64.b64encode(credential_string)])
        return ({
            'Authorization': authorization_val
        }, None)

    @staticmethod
    def _visit_session_security_context(security_context, is_vapi_rest):
        """
        Get the authorization headers for session security context. This is
        currently supported for vapi-rest format only

        :type  security_context: :class:`vmware.vapi.core.SecurityContext`
        :param security_context: Security context
        :type  is_vapi_rest: :class:`bool`
        :param is_vapi_rest: Whether the Rest json message format is VAPI Rest
            or not
        :rtype   :class:`tuple`
        :return: Tuple of HTTP headers and cookies
        """
        if not is_vapi_rest:
            msg = message_factory.get_message(
                'vapi.data.serializers.security_context.unsupported',
                security_context.get(SCHEME_ID))
            raise CoreException(msg)
        session_id = security_context.get(SESSION_ID)
        return ({
            REST_SESSION_ID_KEY: session_id
        }, None)

    @staticmethod
    def _visit_oauth_security_context(security_context, is_vapi_rest):
        """
        Get the authorization headers for oauth security context. This is
        currently supported for skyscraper-rest format only

        :type  security_context: :class:`vmware.vapi.core.SecurityContext`
        :param security_context: Security context
        :type  is_vapi_rest: :class:`bool`
        :param is_vapi_rest: Whether the Rest json message format is VAPI Rest
            or not
        :rtype   :class:`tuple`
        :return: Tuple of HTTP headers and cookies
        """
        if is_vapi_rest:
            msg = message_factory.get_message(
                'vapi.data.serializers.security_context.unsupported',
                security_context.get(SCHEME_ID))
            raise CoreException(msg)
        oauth_token = security_context.get(ACCESS_TOKEN)
        return ({
            'Authorization': 'Bearer {}'.format(oauth_token)
        }, None)


class ResponseDeserializer(object):
    """ REST response deserializer """
    @staticmethod
    def deserialize_response(status, response_str, is_vapi_rest):
        """
        Deserialize the REST response

        :type  status: :class:`int`
        :param status: HTTP response status code
        :type  response_str: :class:`str`
        :param response_str: HTTP response body
        :type  is_vapi_rest: :class:`bool`
        :param is_vapi_rest: Whether the Rest json message format is VAPI Rest
            or not
        :rtype   :class:`vmware.vapi.core.MethodResult`
        :return: VAPI MethodResult
        """
        output, error = None, None
        if response_str is not None and response_str != '':
            response_value = DataValueConverter.convert_to_data_value(
                response_str)
            if status in successful_status_codes:
                # Successful response, create output
                # Skyscraper uses 202 for returning tasks
                if is_vapi_rest:
                    # VAPI REST output has a value wrapper
                    output = response_value.get_field('value')
                else:
                    output = response_value
            else:
                # Create error
                if is_vapi_rest:
                    # VAPI REST error has specific format
                    name = response_value.get_field('type').value
                    values = dict(
                        response_value.get_field('value').get_fields())
                    error = ErrorValue(name=name, values=values)
                else:
                    # For other REST APIs create generic error for now
                    error = ErrorValue(
                        name=http_to_vapi_error_map[status],
                        values={
                            'messages': ListValue(),
                            'data': response_value,
                        })
        else:
            # No response body
            if status == 200:
                output = VoidValue()
        return MethodResult(output=output, error=error)


class RestSerializer(object):
    """
    Rest request de/serializer
    """
    @staticmethod
    def serialize_request(input_value, ctx, rest_metadata, is_vapi_rest):
        """
        Serialize the request as a REST request

        :type  input_value: :class:`vmware.vapi.data.value.StructValue`
        :param input_value: method input parameters
        :type  ctx: :class:`vmware.vapi.core.ExecutionContext`
        :param ctx: execution context object
        :type  rest_metadata:
            :class:`vmware.vapi.lib.rest.OperationRestMetadata`
        :param rest_metadata: Rest request metadata
        :type  is_vapi_rest: :class:`bool`
        :param is_vapi_rest: Whether the Rest json message format is VAPI Rest
            or not
        :rtype   :class:`tuple`
        :return: Tuple of URL path, HTTP headers, request body and cookies
        """
        return RequestSerializer.serialize_request(
            input_value, ctx, rest_metadata, is_vapi_rest)

    @staticmethod
    def deserialize_response(status, response_str, is_vapi_rest):
        """
        Deserialize the REST response

        :type  status: :class:`int`
        :param status: HTTP response status code
        :type  response_str: :class:`str`
        :param response_str: HTTP response body
        :type  is_vapi_rest: :class:`bool`
        :param is_vapi_rest: Whether the Rest json message format is VAPI Rest
            or not
        :rtype   :class:`vmware.vapi.core.MethodResul`
        :return: VAPI MethodResult
        """
        return ResponseDeserializer.deserialize_response(
            status, response_str, is_vapi_rest)
