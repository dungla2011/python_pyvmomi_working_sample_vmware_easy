"""
Wsgi Server
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015-2017, 2020 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import logging
import re
import six
import ssl
import werkzeug
from werkzeug.exceptions import HTTPException
from werkzeug.routing import (Rule, Map)
from werkzeug.wrappers import Request, Response
from wsgiref.simple_server import make_server

from vmware.vapi.data.serializers.cleanjson import DataValueConverter
from vmware.vapi.lib.addr_url_parser import parse_addr_url
from vmware.vapi.lib.constants import (
    JSON_CONTENT_TYPE, JSONRPC)
from vmware.vapi.lib.log import get_vapi_logger, get_provider_wire_logger
from vmware.vapi.lib.std import make_error_value_from_msgs, make_std_error_def
from vmware.vapi.l10n.runtime import message_factory
from vmware.vapi.rest.handler import RESTHandler
from vmware.vapi.server.server_interface import ServerInterface

logger = get_vapi_logger(__name__)
provider_wire_logger = get_provider_wire_logger()


class WsgiApplication(object):
    """
    Python WSGI application. For more details about WSGI
    specification, see PEP 333.
    """
    def __init__(self, msg_handler_map, provider_config):
        """
        Initialize WsgiApplication

        :type  msg_handler_map: :class:`dict` of :class:`str` and
            :class:`vmware.vapi.protocol.server.api_handler.ApiHandler`
        :param msg_handler_map: Map of content type to the message
            handler for that content type
        """
        self._msg_handler_map = msg_handler_map

        jsonrpc_prefix = provider_config.get_jsonrpc_prefix()
        if jsonrpc_prefix:
            routing_rules = [Rule(jsonrpc_prefix, endpoint=JSONRPC)]
        else:
            # No prefix specified, use path converter rule, that matches
            # any prefix.
            # This is used for backcompat as previously, specifying
            # jsonrpc prefix was not required for wsgi applications.
            routing_rules = [Rule('/<path:path>', endpoint=JSONRPC)]

        if provider_config.enable_rest():
            json_msg_handler = self._msg_handler_map.get(JSON_CONTENT_TYPE)
            allow_cookies = provider_config.are_cookies_supported()
            self._rest_handler = RESTHandler(
                json_msg_handler.provider, allow_cookies, provider_config)
            self._rest_prefix = provider_config.get_rest_prefix()
            routing_rules += self._rest_handler.rest_rules

        # There are some request mapping arguments that has '-' in them which
        # is not allowed by werkzeug so change the dashes with '__'
        dash_pattern = re.compile(r'-(?=[^<>]*>)')
        for rule in routing_rules:
            rule.rule = dash_pattern.sub(r'__', rule.rule)

        self.rule_map = Map(routing_rules)
        logger.info(self.rule_map)

    def _handle_jsonrpc_call(self, request):
        """
        Handle a JSONRPC protocol request

        :type  request: :class:`werkzeug.wrappers.Request`
        :param request: Request object
        :rtype: :class:`str`
        :return: output string
        """
        content_type, _ = werkzeug.http.parse_options_header(
            request.content_type)
        handler = self._msg_handler_map.get(content_type)
        if handler is None:
            raise werkzeug.exceptions.BadRequest(
                'Content-Type %s is not supported' % (content_type))
        try:
            result, headers = handler.handle_request(request.get_data(),
                                                     request.headers)
        except Exception as e:
            logger.exception(e)
            raise werkzeug.exceptions.InternalServerError(
                'Unexpected error. See server logs for more details.')
        return result, headers

    def _handle_rest_call(self, request, endpoint, args):
        """
        Handle HTTP REST call

        :type  request: :class:`werkzeug.wrappers.Request`
        :param request: Request object
        :type  endpoint: :class:`str`
        :param endpoint: Tuple of service ID and operation ID
        :type  args: :class:`dict` of :class:`str` and :class:`object`
        :param args: Arguments parsed from the HTTP URL
        :rtype: :class:`tuple` of :class:`str` and :class:`str`
        :return: HTTP status string and output
        """
        # Accept only json content type
        if request.content_length:
            content_type, _ = werkzeug.http.parse_options_header(
                request.content_type)
            if content_type != JSON_CONTENT_TYPE and request.method in [
                    'POST', 'PATCH', 'PUT']:
                raise werkzeug.exceptions.UnsupportedMediaType(
                    '%s content type is not supported' % content_type)
        try:
            output = self._rest_handler.invoke(request, endpoint, args)
        except werkzeug.exceptions.BadRequest as e:
            raise e
        except werkzeug.exceptions.NotFound as e:
            raise e
        except Exception as e:
            logger.exception(e)
            raise werkzeug.exceptions.InternalServerError(
                'Unexpected error. See server logs for more details.')
        return output

    @Request.application
    def __call__(self, request):
        """
        The implementation of WsgiApplication

        :type  request: :class:`werkzeug.wrappers.Request`
        :param request: Request object
        :rtype: :class:`werkzeug.wrappers.Response`
        :return: Response object
        """
        try:
            urls = self.rule_map.bind_to_environ(request.environ)
            endpoint, args = urls.match()
            if provider_wire_logger.isEnabledFor(logging.DEBUG):
                provider_wire_logger.debug(
                    'HTTP %s %s ', request.method, request.url)
                provider_wire_logger.debug(
                    'REQUEST HEADERS: %s', request.headers)
                provider_wire_logger.debug(
                    'REQUEST BODY: %s', request.get_data())
            if endpoint == JSONRPC:
                result, headers = self._handle_jsonrpc_call(request)
                response = Response(result)
                if headers:
                    response.headers = headers
            else:
                status, result, cookies, headers = self._handle_rest_call(
                    request, endpoint, args)
                response = Response(result)
                response.status_code = status
                if headers:
                    response.headers = headers
                if cookies:
                    path = self._rest_prefix
                    for k, v in six.iteritems(cookies):
                        response.set_cookie(k, v, path=path)
            response.content_type = JSON_CONTENT_TYPE
            if provider_wire_logger.isEnabledFor(logging.DEBUG):
                provider_wire_logger.debug(
                    'RESPONSE STATUS: %s', response.status_code)
                provider_wire_logger.debug(
                    'RESPONSE HEADERS: %s', response.headers)
                provider_wire_logger.debug(
                    'RESPONSE BODY: %s', response.response)
            return response
        except HTTPException as e:
            try:
                internal_server_error_def = make_std_error_def(
                    'com.vmware.vapi.std.errors.invalid_request')
                msg = message_factory.get_message('vapi.method.invoke.exception',    # pylint: disable=line-too-long
                                                  e.description)
                error_value = make_error_value_from_msgs(
                              internal_server_error_def, msg)
                json_output = DataValueConverter.convert_to_json(error_value)
                response = e.get_response()
                response.set_data(json_output)
                response.headers['Content-Type'] = 'application/json'
                return response
            except Exception:
                # if there is error in serialize the error,
                # just return the original raw exception
                return e


class WsgiServer(ServerInterface):
    """
    Server wrapper class for Wsgi application.
    """

    SUPPORTED_SCHEMES = ('http', 'https')
    HTTP_CONTENT_MAPPING = {'json': 'application/json',
                            'xml': 'text/xml',
                            '': ''}

    def __init__(self):
        """
        Initialize WsgiServer
        """
        self._protocol_handler_map = {}
        self._url = None
        self._wsgi_application = None
        self._http_server = None
        self.provider_config = None
        ServerInterface.__init__(self)

    def register_handler(self, addr, msg_type, protocol_handler, ssl_args=None):
        """
        Register protocol handler

        :type  addr: :class:`str`
        :param addr: addr url
        :type  msg_type: :class:`str`
        :param msg_type: protocol message type
        :type  protocol_handler: :class:`vmware.vapi.protocol.server.transport.\
            async_protocol_handler.AsyncProtocolHandler`
        :param protocol_handler: protocol handler for this addr
        :type  ssl_args: :class:`dict`
        :param ssl_args: ssl arguments
        """
        assert(protocol_handler)
        content_type = self.HTTP_CONTENT_MAPPING.get(msg_type)
        if content_type is None:
            logger.error('Unsupported msg type: %s', msg_type)
            return
        self._protocol_handler_map[content_type] = protocol_handler
        self._url = addr
        self._ssl_args = ssl_args

    def get_wsgi_application(self):
        """
        Returns the WSGI application.

        :rtype: :class:`vmware.vapi.server.wsgi_server.WsgiApplication`
        :return: WSGI application.
        """
        if self._wsgi_application is None:
            assert(self.provider_config)
            self._wsgi_application = WsgiApplication(
                self._protocol_handler_map, self.provider_config)
        return self._wsgi_application

    def serve_forever(self):
        _, host, port, _, _, _, _ = parse_addr_url(self._url)
        self._http_server = make_server(host, port, self.get_wsgi_application())
        if self._ssl_args:
            self._http_server.socket = ssl.wrap_socket(
                self._http_server.socket, keyfile=self._ssl_args['keyfile'],
                certfile=self._ssl_args['certfile'], server_side=True)
        logger.info('Listening on: %s', self._url)
        self._http_server.serve_forever()

    def shutdown(self):
        self._http_server.shutdown()


def get_server():
    """
    Get wsgi server

    :rtype: :class:`vmware.vapi.server.server_interface.ServerInterface`
    :return: subclass of ServerInterface
    """
    return WsgiServer()
