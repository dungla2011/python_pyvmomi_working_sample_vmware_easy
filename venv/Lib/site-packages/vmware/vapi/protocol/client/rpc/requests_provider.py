"""
RPC Provider using Requests Library
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015-2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long


import requests

from vmware.vapi.lib.log import get_vapi_logger
from vmware.vapi.protocol.client.http_lib import HTTPMethod, HTTPResponse
from vmware.vapi.protocol.client.rpc.provider import HTTPProvider

logger = get_vapi_logger(__name__)


class RequestsRpcProvider(HTTPProvider):
    """
    vAPI RPC provider using requests library
    """
    _http_method_map = {
        HTTPMethod.DELETE: 'delete',
        HTTPMethod.GET: 'get',
        HTTPMethod.HEAD: 'head',
        HTTPMethod.OPTIONS: 'options',
        HTTPMethod.PATCH: 'patch',
        HTTPMethod.POST: 'post',
        HTTPMethod.PUT: 'put'
    }

    def __init__(self, session, base_url, default_timeout, pool_size):
        """
        Initialize RequestsRpcProvider

        :type  session: :class:`requests.Session`
        :param session: Session object
        :type  msg_protocol: :class:`str`
        :param msg_protocol: Message protocol to be used for the connection.
                             Valid values are 'json'.
        :type  base_url: :class:`str`
        :param base_url: HTTP(S) URL to be used
        :type  default_timeout: :class:`int`
        :param default_timeout: Request default timeout
        :type  pool_size: :class:`int`
        :param pool_size: Connection pool size to be used
        """
        HTTPProvider.__init__(self)
        self._session = session
        self._base_url = base_url[:-1] if base_url.endswith('/') else base_url
        self._pool_size = pool_size
        self._default_timeout = default_timeout
        if pool_size:
            http_adapter = requests.adapters.HTTPAdapter(
                pool_connections=pool_size,
                pool_maxsize=pool_size)
            https_adapter = requests.adapters.HTTPAdapter(
                pool_connections=pool_size,
                pool_maxsize=pool_size)
            self._session.mount('http://', http_adapter)
            self._session.mount('https://', https_adapter)

    def __del__(self):
        """ Requests rpc provider on delete """
        self.disconnect()

    def connect(self):
        """
        connect

        :rtype: :class:`vmware.vapi.protocol.client.rpc.provider.RpcProvider`
        :return: http rpc provider
        """
        return self

    def disconnect(self):
        """ disconnect """
        pass

    def do_request(self, http_request):
        """
        Send an HTTP request

        :type  http_request: :class:`vmware.vapi.protocol.client.http_lib.HTTPRequest`
        :param http_request: The http request to be sent
        :rtype: :class:`vmware.vapi.protocol.client.http_lib.HTTPResponse`
        :return: The http response received
        """
        method_name = http_request.method
        if http_request.url_path:
            url = ''.join([self._base_url, http_request.url_path])
        else:
            url = self._base_url
        timeout = http_request.timeout if http_request.timeout else self._default_timeout
        output = self._session.request(
            method=self._http_method_map[method_name], url=url,
            data=http_request.body, headers=http_request.headers,
            cookies=http_request.cookies, timeout=timeout)
        output.encoding = 'utf-8'
        return HTTPResponse(output.status_code, output.headers, output.text,
                            output)
