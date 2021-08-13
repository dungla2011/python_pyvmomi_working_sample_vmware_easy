"""
Json client handler
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015-2019 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long


import itertools
import six

from vmware.vapi.core import ApiProvider
from vmware.vapi.protocol.client.http_lib import HTTPMethod, HTTPRequest
from vmware.vapi.protocol.client.msg.generic_connector import GenericConnector
from vmware.vapi.lib.constants import (HTTP_USER_AGENT_HEADER, JSON_CONTENT_TYPE,    # pylint: disable=line-too-long
                                       HTTP_CONTENT_TYPE_HEADER)
from vmware.vapi.lib.load import dynamic_import_list
from vmware.vapi.lib.log import get_client_wire_logger, get_vapi_logger
from vmware.vapi.protocol.client.msg.user_agent_util import get_user_agent

from vmware.vapi.data.serializers.jsonrpc import (
    JsonRpcDictToVapi,
    vapi_jsonrpc_request_factory, deserialize_response,
    vapi_jsonrpc_error_transport_error,
    VAPI_INVOKE
)

logger = get_vapi_logger(__name__)
request_logger = get_client_wire_logger()


class JsonClientProvider(ApiProvider):
    """ Json rpc client provider """

    def __init__(self, http_provider, post_processors):
        """
        Json rpc client provider init

        :type  http_provider:
            :class:`vmware.vapi.protocol.client.rpc.provider.HTTPProvider`
        :param http_provider: rpc provider object
        :type  post_processors: :class:`list` of :class:`str`
        :param post_processors: List of post processor class names
        """

        ApiProvider.__init__(self)
        self.http_provider = http_provider
        self.counter = itertools.count()
        self.to_vapi = JsonRpcDictToVapi

        # Load all the post processors
        self.post_processors = [
            constructor()
            for constructor in dynamic_import_list(post_processors)]

    def invoke(self, service_id, operation_id, input_value, ctx):
        """
        Invokes the specified method using the input value and the
        the execution context provided

        :type  service_id: :class:`str`
        :param service_id: Service identifier
        :type  operation_id: :class:`str`
        :param operation_id: Operation identifier
        :type  input_value: :class:`vmware.vapi.data.value.DataValue`
        :param input_value: method input parameters
        :type  ctx: :class:`vmware.vapi.core.ExecutionContext`
        :param ctx: execution context object
        :rtype: :class:`vmware.vapi.core.MethodResult`
        :return: method result object
        """

        params = {
            'serviceId': service_id,
            'operationId': operation_id,
            'input': input_value,
            'ctx': ctx,
        }
        response = self._do_request(VAPI_INVOKE, ctx, params)
        result = self.to_vapi.method_result(response.result)
        return result

    #
    ## vapi methods end

    def _do_request(self, method, ctx, params=None):
        """
        Perform json rpc request

        :type  method: :class:`str`
        :param method: json rpc method name
        :type  ctx: :class:`vmware.vapi.core.ExecutionContext`
        :param ctx: execution context object
        :type  params: :class:`dict` or None
        :param params: json rpc method params
        :rtype: :class:`vmware.vapi.data.serializer.jsonrpc.JsonRpcResponse`
        :return: json rpc response
        """

        logger.debug('_do_request: request %s', method)

        if not self.http_provider.connect():
            logger.error('Connection refused')
            raise vapi_jsonrpc_error_transport_error()
        request_headers = {HTTP_CONTENT_TYPE_HEADER: JSON_CONTENT_TYPE,
                           HTTP_USER_AGENT_HEADER: get_user_agent()}
        id_ = six.advance_iterator(self.counter)    # atomic increment
        id_ = str(id_)    # TODO: Bypass java barf temporary
        request = vapi_jsonrpc_request_factory(method=method,
                                               params=params,
                                               id=id_)
        request_body = request.serialize()
        if six.text_type:
            request_body = request_body.encode('utf-8')
        for processor in self.post_processors:
            request_body = processor.process(request_body)

        request_logger.debug('_do_request: request %s', request_body)
        # do_request returns http_response
        http_response = self.http_provider.do_request(
            HTTPRequest(method=HTTPMethod.POST, url_path=None,
                        headers=request_headers, body=request_body))
        if http_response.data is not None:
            # Currently only RequestsProvider returns the requests Response
            # object as data back. We need to raise exception if error is
            # returned to keep existing behavior.
            http_response.data.raise_for_status()
        request_logger.debug('_do_request: response %s', http_response.body)

        if ctx.runtime_data is not None:
            response_extractor = ctx.runtime_data.get('response_extractor')
            if response_extractor is not None:
                response_extractor.set_http_status(http_response.status)
                response_extractor.set_http_headers(http_response.headers)
                response_extractor.set_http_body(http_response.body)
                response_extractor.set_http_method(HTTPMethod.POST)
                response_extractor.set_http_url(self.http_provider._base_url)    # pylint: disable=protected-access

        response = deserialize_response(http_response.body)
        request.validate_response(response)
        if response.error is not None:
            logger.error('_do_request: method %s response with error %s',
                         method, response.error)
            raise response.error  # pylint: disable=E0702
        return response


def get_protocol_connector(
        http_provider, post_processors=None, provider_filter_chain=None):
    """
    Get protocol connector

    :type  http_provider:
        :class:`vmware.vapi.protocol.client.rpc.provider.HTTPProvider`
    :param http_provider: rpc provider object
    :type  post_processors: :class:`list` of :class:`str`
    :param post_processors: List of post processor class names
    :type  provider_filter_chain: :class:`list` of
        :class:`vmware.vapi.provider.filter.ApiProviderFilter`
    :param provider_filter_chain: List of API filters in order they are to be
        chained
    :rtype: :class:`vmware.vapi.protocol.client.connector.Connector`
    :return: json rpc connector object
    """
    if post_processors is None:
        post_processors = []
    api_provider = JsonClientProvider(http_provider, post_processors)
    connector = GenericConnector(
        http_provider, api_provider, provider_filter_chain)
    return connector
