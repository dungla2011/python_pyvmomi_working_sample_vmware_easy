"""
Http protocol rpc provider
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015-2017, 2019 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long


import socket
from six.moves import urllib
from six.moves import http_client

from vmware.vapi.protocol.client.http_lib import HTTPResponse
from vmware.vapi.protocol.client.rpc.provider import HTTPProvider
from vmware.vapi.lib.addr_url_parser import parse_addr_url
from vmware.vapi.lib.log import get_vapi_logger

logger = get_vapi_logger(__name__)

# Constant definitions
NUM_OF_POOL = 10
POOL_SIZE = 8
CONNECTION_POOL_TIMEOUT = 8 * 60    # 8 minutes

use_connection_pool = True
try:
    from urllib3 import PoolManager
except ImportError:
    use_connection_pool = False
    logger.info('Can not load urllib3 module, disable connection pool')


#
# Temporary workaround for Bug 1222549
#
# When client and server are using HTTP 1.1 with chunked encoding. Once server
# sends all the data, it should sent a zero length chunk to indicate to the
# client that server has sent all the data. In this case, if server closes the
# session without sending a zero length chunk, client throws IncompleteRead
# error.
#
# However, the issue is intermittent and is not reproducable.
#
# A possible fix has been suggested here:
# http://bobrochel.blogspot.com/2010/11/bad-servers-chunked-encoding-and.html
# i.e. Read the partial data and don't complain if we don't receive the zero
# length chunk.
#
#
def patch_http_response_read(func):
    """
    Wrapper function to patch the http read method to return the partial data
    when the server doesn't send a zero length chunk
    """
    def inner(*args):
        """
        Function that implements the patch
        """
        try:
            return func(*args)
        except http_client.IncompleteRead as e:
            logger.exception('Did not receive zero length chunk from the server')    # pylint: disable=line-too-long
            return e.partial
    return inner


http_client.HTTPResponse.read = patch_http_response_read(http_client.HTTPResponse.read)    # pylint: disable=line-too-long


class UnixSocketConnection(http_client.HTTPConnection):
    """
    Variant of http_client.HTTPConnection that supports HTTP
    connections over Unix domain sockets.
    """

    def __init__(self, path):
        """
        Initialize a Unix domain socket HTTP connection

        The HTTPConnection __init__ method expects a single argument,
        which it interprets as the host to connect to.  For this
        class, we instead interpret the parameter as the filesystem
        path of the Unix domain socket.

        :type    path: :class:`str`
        :param   path: Unix domain socket path
        """

        # Pass '' as the host to HTTPConnection; it doesn't really matter
        # what we pass (since we've overridden the connect method) as long
        # as it's a valid string.
        http_client.HTTPConnection.__init__(self, '')
        self.path = path
        self.sock = None

    def connect(self):
        """
        Override the HTTPConnection connect method to connect to a
        Unix domain socket.  Obey the same contract as HTTPConnection.connect
        which puts the socket in self.sock.
        """

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self.path)
        self.sock = sock


class HttpRpcProvider(HTTPProvider):
    """ http rpc provider """

    def __init__(self, ssl_args, url, disable_conn_pool=False):
        """
        http rpc provider init

        :type  ssl_args: :class:`dict`
        :param ssl_args: ssl arguments
        :type  url: :class:`str`
        :param url: url to connected to
        :type disable_conn_pool: :class: 'bool'
        :param disable_conn_pool: disable connection pooling
        """
        HTTPProvider.__init__(self)
        self.ssl_enabled = False
        self.ssl_args = ssl_args

        scheme, host, port, user, password, path, _ = parse_addr_url(url)
        assert(scheme in ['http', 'https'])
        if scheme == 'https':
            self.ssl_enabled = True
        assert(user is None and password is None)    # NYI
        if host.startswith('!'):
            # Unix domain socket: hostname is '!' followed by
            # the URL-encoded socket path
            self.host = None
            self.uds = urllib.parse.unquote(host[1:])
            # SSL currently not supported for Unix domain sockets
            if self.ssl_enabled:
                raise Exception('SSL not supported on Unix domain sockets')
        else:
            self.host = host
            self.port = port
            self.uds = None
        self.path = path
        self.cookie = ''
        self.accept_compress_response = True

        global use_connection_pool
        if disable_conn_pool:
            use_connection_pool = False

        if self.uds is None and use_connection_pool:
            self.manager = PoolManager(num_pools=NUM_OF_POOL,
                                       maxsize=POOL_SIZE,
                                       timeout=CONNECTION_POOL_TIMEOUT,
                                       **self.ssl_args)

    def __del__(self):
        """ http rpc provider on delete """
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
        if use_connection_pool and self.manager is not None:
            self.manager.clear()

    def _get_connection(self):
        """
        get connection from pool

        :rtype: :class:`PoolManager` (or)
            :class:`UnixSocketConnection`
        :return: http(s) connection or unix socket connection
        """
        conn = None

        if self.uds:
            conn = UnixSocketConnection(self.uds)
        elif use_connection_pool:
            http_scheme = 'http'
            if self.ssl_enabled:
                http_scheme = 'https'
            conn = self.manager.connection_from_host(host=self.host,
                                                     port=self.port,
                                                     scheme=http_scheme)
        else:
            if self.ssl_enabled:
                conn = http_client.HTTPSConnection(host=self.host,
                                                   port=self.port,
                                                   **self.ssl_args)
            else:
                conn = http_client.HTTPConnection(host=self.host,
                                                  port=self.port)

        return conn

    def do_request(self, http_request):
        """
        Send an HTTP request

        :type  http_request: :class:`vmware.vapi.protocol.client.http_lib.HTTPRequest`    # pylint: disable=line-too-long
        :param http_request: The http request to be sent
        :rtype: :class:`vmware.vapi.protocol.client.http_lib.HTTPResponse`
        :return: The http response received
        """
        # pylint can't detect request, getresponse and close methods from
        # Http(s)Connection/UnixSocketConnection
        # pylint: disable=E1103
        request_ctx = http_request.headers
        request = http_request.body
        content_type = request_ctx.get('Content-Type')
        if not content_type:
            # For http, content-type must be set
            raise Exception('do_request: request_ctx content-type not set')

        response_ctx, response = {'Content-Type': content_type}, None
        if request:
            request_length = len(request)
            # Send request
            headers = {'Cookie': self.cookie,
                       'Content-Type': content_type}
            if self.accept_compress_response:
                headers['Accept-Encoding'] = 'gzip, deflate'

            try:
                conn = self._get_connection()
                logger.debug('do_request: request_len %d', request_length)

                if use_connection_pool:
                    resp = conn.request(method=http_request.method,
                                        url=self.path,
                                        body=request,
                                        headers=headers,
                                        preload_content=False)
                else:
                    conn.request(method=http_request.method,
                                 url=self.path,
                                 body=request,
                                 headers=headers)
                    resp = conn.getresponse()
            except:
                logger.exception('do_request() failed')
                raise

            # Debug
            # logger.debug('do_request: response headers', resp.getheaders())

            cookie = resp.getheader('Set-Cookie')
            if cookie:
                self.cookie = cookie

            status = resp.status
            if status in [200, 500]:
                try:
                    encoding = resp.getheader('Content-Encoding', 'identity').lower()    # pylint: disable=line-too-long
                    if encoding in ['gzip', 'deflate']:
                        response = resp.read(decode_content=True)
                    else:
                        response = resp.read()

                    logger.debug('do_request: response len %d', len(response))
                except:
                    conn.close()
                    raise
                else:
                    if resp:
                        resp.read()

                content_type = resp.getheader('Content-Type')
                if content_type:
                    response_ctx['Content-Type'] = content_type
            else:
                raise http_client.HTTPException('%d %s' % (resp.status, resp.reason))    # pylint: disable=line-too-long

            if self.cookie:
                response_ctx['Cookie'] = self.cookie
        return HTTPResponse(status=status, headers=response_ctx, body=response)
