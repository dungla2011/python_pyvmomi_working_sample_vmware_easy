"""
Json rpc server side handler
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015-2017, 2019 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long


import traceback

from vmware.vapi.common.context import set_context, clear_context
from vmware.vapi.data.serializers.jsonrpc import (
   JsonRpcDictToVapi, JsonRpcError, vapi_jsonrpc_response_factory,
   vapi_jsonrpc_error_invalid_request, vapi_jsonrpc_error_parse_error,
   vapi_jsonrpc_error_internal_error, vapi_jsonrpc_error_method_not_found,
   vapi_jsonrpc_error_invalid_params, vapi_jsonrpc_error_invalid_operation,
   deserialize_request, VAPI_INVOKE)
from vmware.vapi.lib.constants import (
    HTTP_ACCEPT_LANGUAGE, HTTP_FORMAT_LOCALE, HTTP_TIMEZONE, LOCALE,
    header_mapping_dict, VAPI_ERROR_HEADER, VAPI_HEADER_PREFIX,
    VAPI_OPERATION_HEADER, VAPI_SERVICE_HEADER, VAPI_SESSION_HEADER)
from vmware.vapi.lib.context import (
    create_default_application_context, insert_header, insert_operation_id)
from vmware.vapi.lib.load import dynamic_import_list
from vmware.vapi.lib.log import get_vapi_logger
from vmware.vapi.lib.profiler import profile
from vmware.vapi.protocol.server.api_handler import ApiHandler
from vmware.vapi.security.session import create_session_security_context

logger = get_vapi_logger(__name__)


class JsonApiHandler(ApiHandler):
    """ Json rpc api handler """

    def __init__(self, provider, pre_processors):
        """
        Json rpc api handler init

        :type  provider: :class:`vmware.vapi.core.ApiProvider`
        :param provider: api provider object
        :type  pre_processors: :class:`list` of :class:`str`
        :param pre_processors: List of pre processor class names
        """
        ApiHandler.__init__(self)
        self.ops = {
            VAPI_INVOKE: self.invoke,
        }
        self.provider = provider
        self.to_vapi = JsonRpcDictToVapi

        # Load all the pre processors
        self.pre_processors = [
            constructor()
            for constructor in dynamic_import_list(pre_processors)]

    @profile
    def handle_request(self, request_str, headers=None):
        """
        Handle a vapi request

        :type  request_str: :class:`str`
        :param request_str: json rpc request string
        :type  headers: :class:`dict`
        :param headers: request headers
        :rtype: :class:`str`
        :return: response string
        """
        request = None
        request_method = None
        response_str = None
        response_headers = {}

        try:
            # Execute all the pre processors
            try:
                for processor in self.pre_processors:
                    request_str = processor.process(request_str)
            except Exception as err:
                logger.debug('Encountered error during preprocessing'
                             'of JSON request')
                raise vapi_jsonrpc_error_invalid_request(err)

            try:
                request = deserialize_request(request_str)
            except JsonRpcError as err:
                raise
            except Exception as err:
                logger.debug('Deserialize error')
                raise vapi_jsonrpc_error_parse_error(err)

            try:
                request_method = request.method
                handler = self.ops[request_method]
            except KeyError as err:
                # No such method
                logger.error('No such method: %s', request_method)
                raise vapi_jsonrpc_error_method_not_found()

            # Invoke method
            result = handler(request, headers)

            if not result.success():
                response_headers[VAPI_ERROR_HEADER] = result.error.name

            # Serialize response
            response = vapi_jsonrpc_response_factory(request, result=result)
            response_str = response.serialize()
        except JsonRpcError as err:
            logger.debug('JsonRpcError callstack: %s: %s',
                         request_method, traceback.format_exc())
            response = vapi_jsonrpc_response_factory(request, error=err)
            response_str = response.serialize()
        #except CoreException, err:
        #    # NYI: We should *NEVER* see the core exception. Just in case, we
        #    # should do the right thing
        #    # For now, treated as normal Exception
        #    logger.debug('Core exception callstack: %s: %s',
        #                                request_method, traceback.format_exc())
        except Exception as err:
            # All other errors => internal server error
            logger.debug('Exception callstack: %s: %s',
                         request_method, traceback.format_exc())
            error = vapi_jsonrpc_error_internal_error(str(err))
            response = vapi_jsonrpc_response_factory(request, error=error)
            response_str = response.serialize()

        return response_str, response_headers

    @staticmethod
    def _verify_no_input_params(request):
        """
        Verify no input params is given

        :type  request:
            :class:`vmware.vapi.data.serializer.jsonrpc.JsonRpcRequest`
        :param request: json rpc request
        """
        if request.params:
            logger.error('Unexpected input params %s', request.method)
            raise vapi_jsonrpc_error_invalid_params()

    def _verify_operation_headers(self, headers, service_id, operation_id):
        """
        Validate service id and operation id in request body match the one in
        the headers

        :type  headers: :class:`dict`
        :param headers: Request headers
        :type  service_id: :class:`str`
        :param service_id: Service Id
        :type  operation_id: :class:`str`
        :param operation_id: Operation Id
        """
        service_header = headers.get(VAPI_SERVICE_HEADER)
        operation_header = headers.get(VAPI_OPERATION_HEADER)

        if service_header is None and operation_header is None:
            return None

        if not service_id or not operation_id:
            logger.error('Missing service id or operation id from request')
            raise vapi_jsonrpc_error_invalid_params()

        if service_header != service_id or operation_header != operation_id:
            logger.error('Mismatch between service id or operation id in '
                         'request and headers')
            raise vapi_jsonrpc_error_invalid_operation()

        return None

    def _copy_vapi_context_headers(self, headers, ctx):
        """
        Copy vAPI context headers from request header to application context.
        Override existing application context values if key already exists.

        :type  headers: :class:`dict`
        :param headers: Request headers
        :type  ctx: :class:`vmware.vapi.core.ExecutionContext`
        :param ctx: Execution Context
        """
        for k, v in headers.items():
            header = k.lower()
            if header.startswith(VAPI_HEADER_PREFIX):
                header_name_split = header.split(VAPI_HEADER_PREFIX)
                header = header_mapping_dict.get(header_name_split[1],
                                                 header_name_split[1])
                insert_header(ctx.application_context, header, v)

        for k, v in headers.items():
            if k.lower() == 'user-agent':
                # Special handling for 'user-agent' header
                insert_header(ctx.application_context, '$userAgent', v)
            elif k.lower() == HTTP_ACCEPT_LANGUAGE:
                insert_header(ctx.application_context, LOCALE, v)
            elif k.lower() == HTTP_FORMAT_LOCALE:
                insert_header(ctx.application_context, HTTP_FORMAT_LOCALE, v)
            elif k.lower() == HTTP_TIMEZONE:
                insert_header(ctx.application_context, HTTP_TIMEZONE, v)

    def _copy_vapi_session_header(self, headers, ctx):
        """
        Copy session id from request header to security context.
        Override if session id already exists in security context.

        :type  headers: :class:`dict`
        :param headers: Request headers
        :type  ctx: :class:`vmware.vapi.core.ExecutionContext`
        :param ctx: Execution Context
        """
        session_id = headers.get(VAPI_SESSION_HEADER)
        if session_id is not None:
            ctx.security_context = create_session_security_context(session_id)

    def invoke(self, request, headers=None):
        """
        Invokes a specified method given an execution context, a method
        identifier and method input parameter(s)

        :type  request:
            :class:`vmware.vapi.data.serializer.jsonrpc.JsonRpcRequest`
        :param request: json rpc request object
        :rtype: :class:`dict`
        :return: Result of the method invocation
        """
        try:
            params = request.params
            service_id = str(params.get('serviceId', ''))
            operation_id = str(params.get('operationId', ''))
            input_value = self.to_vapi.data_value(params.get('input'))
            ctx = self.to_vapi.execution_context(params.get('ctx'))
            if ctx.application_context is None:
                ctx.application_context = create_default_application_context()
            else:
                insert_operation_id(ctx.application_context)

            if headers is not None:
                self._verify_operation_headers(headers, service_id,
                                               operation_id)
                self._copy_vapi_context_headers(headers, ctx)
                self._copy_vapi_session_header(headers, ctx)

            set_context(ctx)
        except JsonRpcError as err:
            raise err
        except Exception:
            raise vapi_jsonrpc_error_invalid_params()

        # Invoke method
        invoke_result = self.provider.invoke(
            service_id, operation_id, input_value, ctx)

        #Reset context from logging
        clear_context()

        # Build result
        return invoke_result


def get_protocol_handler(provider, pre_processors=None):
    """
    Get protocol handler

    :type  provider: :class:`vmware.vapi.core.ApiProvider`
    :param provider: api provider object
    :type  pre_processors: :class:`list` of :class:`str`
    :param pre_processors: List of pre processor class names
    :rtype :class:`vmware.vapi.protocol.server.api_handler.ApiHandler`
    :return: json rpc api handler object
    """
    if pre_processors is None:
        pre_processors = []
    api_handler = JsonApiHandler(provider, pre_processors)
    return api_handler
