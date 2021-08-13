"""
Twisted server
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015, 2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import threading
import six
import warnings

with warnings.catch_warnings():
    # Disable DeprecationWarning as twisted uses md5 instead of hashlib
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    # Disable SyntaxWarning as twisted uses assert (oldChild.parentNode is self)
    # which is always true
    warnings.filterwarnings("ignore", category=SyntaxWarning)
    import twisted
    # Without adding this explicit import, the ssl part of twisted
    # doesn't get initialized
    import twisted.internet.ssl
    from twisted.internet import defer
    from twisted.internet.protocol import Protocol, Factory
    from twisted.web.resource import Resource
    from twisted.web.server import Site

from vmware.vapi.server.server_interface import ServerInterface
from vmware.vapi.lib.addr_url_parser import parse_addr_url
from vmware.vapi.lib.log import get_vapi_logger

# Try to use epoll if available
try:
    twisted.internet.epollreactor.install()
except Exception:
    pass

# Twisted log
#import sys
#twisted.python.log.startLogging(sys.stdout, setStdout=False)

# NYI: Debug
# import time

logger = get_vapi_logger(__name__)

# Singleton twisted server
_server_lock = threading.Lock()
_twisted_server = None


class TwistedConnectionAdapter(object):
    """ Twisted connection adapter """

    def __init__(self, transport):
        """
        Twisted connection adapter init

        :type  transport: :class:`twisted.internet.interfaces.ITransport`
        :param transport: Twisted transport
        """
        self.transport = transport

    def write(self, data):
        """
        write

        :type  data: :class:`str`
        :param data: data to write
        """
        # Only need to do this for async protocol
        self.transport.reactor.callFromThread(self._write, data)

    def close(self):
        """ close """
        # Only need to do this for async protocol
        self.transport.reactor.callFromThread(self._close)

    def _write(self, data):
        """
        Internal write

        :type  data: :class:`str`
        :param data: data to write
        """
        self.transport.write(data)

    def _close(self):
        """ Internal close """
        self.transport.loseConnection()
        self.transport = None


class TwistedAsyncProtocolHandlerAdapter(Protocol):  # pylint: disable=W0232
    """ Twisted async protocol handler adapter """

    def connectionMade(self):
        """ connection established callback """
        connection = TwistedConnectionAdapter(self.transport)
        self.data_handler = self.factory.protocol_handler.get_data_handler(
            connection)

    def dataReceived(self, data):
        """
        data received

        :type  data: :class:`str`
        :param data: data to write
        """
        self.data_handler.data_ready(data)

    def connectionLost(self, reason):  # pylint: disable=W0222
        """
        Twisted connection lost

        :type  reason: :class:`str`
        :param reason: Connection lost reason
        """
        if issubclass(twisted.internet.error.ConnectionDone, reason.type):
            logger.debug('connectionLost: reason %s', reason)
            self.data_handler.data_end()
        else:
            logger.error('connectionLost: reason %s', reason)
            self.data_handler.data_abort()
        self.data_handler = None  # pylint: disable=W0201


class TwistedVmwareProtocolFactory(Factory):
    """ Twisted vmacre protocol factory """
    protocol = TwistedAsyncProtocolHandlerAdapter

    def __init__(self, protocol_handler):
        """
        Twisted vmacre protocol factory init

        :type  protocol_handler: :class:`vmware.vapi.protocol.server.transport.\
            async_protocol_handler.AsyncProtocolHandler`
        :param protocol_handler: protocol handler for this addr
        """
        self.protocol_handler = protocol_handler


class TwistedHttpConnectionAdapter(object):
    """ Twisted http connection adapter """

    def __init__(self, request):
        """
        Twisted http connection init

        :type  request: :class:`twisted.web.http.Request`
        :param request: Twisted http request object
        """
        self.request = request

    def write(self, data):
        """
        write

        :type  data: :class:`str`
        :param data: data to write
        """
        self.request.transport.reactor.callFromThread(self._write, data)

    def close(self):
        """ close """
        self.request.transport.reactor.callFromThread(self._close)

    # Connection interface
    def _write(self, data):
        """ Internal write """
        if not self.request.finished:
            # NYI: Debug only
            # logger.debug('%f: write data %d', time.time(), len(data))
            self.request.write(data)

    def _close(self):
        """ Internal close """
        if not self.request.finished:
            # NYI: Debug only
            # logger.debug('%f: request.finish()', time.time())
            self.request.setResponseCode(200)
            self.request.finish()


class TwistedVapiResource(Resource):
    """ Twisted vapi resource """

    def __init__(self):
        """ Twisted vapi resource init """
        Resource.__init__(self)
        self.handler_map = {}

    def add_handler(self, content_type, protocol_handler):
        """
        add content handler

        :type  content_type: :class:`str`
        :param content_type: MIME content type
        :type  protocol_handler: :class:`vmware.vapi.protocol.server.transport.\
            async_protocol_handler.AsyncProtocolHandler`
        :param protocol_handler: protocol handler for this path
        """
        curr_handler = self.handler_map.get(content_type)
        if curr_handler:
            if curr_handler != protocol_handler:
                logger.error(
                    'Already registered. Failed to add handler for '
                    'content type %s', content_type)
                return False

        self.handler_map[content_type] = protocol_handler
        return True

    def render_POST(self, request):  # pylint: disable=invalid-name
        """
        Handle POST

        :type  request: :class:`twisted.web.http.Request`
        :param request: Twisted http request object
        """
        # Multiplex depends on content-type
        header_content_type = request.getHeader(b'Content-Type').decode('utf-8')
        tokens = header_content_type.split(';', 1)
        if len(tokens) > 1:
            content_type, _ = tokens
        else:
            content_type = tokens[0]
        handler = self.handler_map.get(content_type)
        if not handler:
            self.handle_error(b'', request, 500, b'Unsupported content')
            return

        request.setHeader(b'Server', b'Twisted/1.0')
        request.setHeader(b'Content-Type', content_type.encode('utf-8'))

        d = defer.Deferred()  # pylint: disable=invalid-name
        d.addCallback(self.handle_read)
        d.addCallback(self.handle_request, request, handler)
        d.addErrback(self.handle_error, request, 500, b'Request failed')
        # NYI: Add timeout for this connection
        # NYI: Add blacklist to protect from DoS attack

        d.callback(request)
        return twisted.web.server.NOT_DONE_YET

    def render_GET(self, request):  # pylint: disable=invalid-name
        """
        Handle HTTP GET

        :type  request: :class:`twisted.web.http.Request`
        :param request: Twisted http request object
        """
        header_content_type = request.getHeader(b'Content-Type').decode('utf-8')
        if header_content_type is None:
            content_type = ''
        else:
            tokens = header_content_type.split(';', 1)
            if len(tokens) > 1:
                content_type, _ = tokens
            else:
                content_type = tokens[0]
            request.setHeader(b'Content-Type', content_type.encode('utf-8'))

        request.setHeader(b'Server', b'Twisted/1.0')
        handler = self.handler_map.get(content_type)
        if not handler:
            self.handle_error(b'', request, 500, b'Unsupported content')
            return

        d = defer.Deferred()  # pylint: disable=invalid-name
        d.addCallback(self.handle_read)
        d.addCallback(self.handle_request, request, handler)
        d.addErrback(self.handle_error, request, 500, b'Request failed')
        # NYI: Add timeout for this connection
        # NYI: Add blacklist to protect from DoS attack

        d.callback(request)
        return twisted.web.server.NOT_DONE_YET

    def handle_error(self, failure, request, response_code, text_msg):  # pylint: disable=R0201
        """
        Handle error

        :type  failure: :class:`twisted.python.failure.Failure`
        :param failure: Twisted failure instance
        :type  request: :class:`twisted.web.http.Request`
        :param request: Twisted http request object
        :type  response_code: :class:`int`
        :param response_code: Http response code
        :type  text_msg: :class:`int`
        :param text_msg: Http error code
        """
        if not request.finished:
            logger.error(
                'handle_error: %s %d %s', failure, response_code, text_msg)
            request.setResponseCode(response_code)
            request.setHeader(b'Content-Type', b'text')
            request.write(text_msg)
            request.finish()

    def handle_read(self, request):  # pylint: disable=R0201
        """
        Handle read

        :type  request: :class:`twisted.web.http.Request`
        :param request: Twisted http request object
        """
        # logger.debug('handle_read:')
        # NYI: Chunking read, and send data one chunk at a time
        return request.content.read()

    def handle_request(self, request_msg, request, handler):  # pylint: disable=R0201
        """
        Handle request

        :type  request_msg: :class:`str`
        :param request_msg: Request msg
        :type  request: :class:`twisted.web.http.Request`
        :param request: Twisted http request object
        :type  handler: :class:`vmware.vapi.protocol.server.transport.\
            async_protocol_handler.AsyncProtocolHandler`
        :param handler: protocol handler for this addr
        """
        # logger.debug('handle_request: %s', request_msg)
        connection = TwistedHttpConnectionAdapter(request)
        data_handler = handler.get_data_handler(connection)
        data_handler.data_ready(request_msg)
        data_handler.data_end()


class TwistedHttpSite(Site):
    """ Twisted http site """
    HTTP_CONTENT_MAPPING = {'json': 'application/json',
                            'xml': 'text/xml',
                            '': ''}

    def __init__(self):
        """ Http site site init """
        self.root_resource = twisted.web.resource.Resource()
        twisted.web.server.Site.__init__(self, self.root_resource)

    def add_res_handler(self, path, msg_type, protocol_handler):
        """
        Add resource handler for a path

        :type  path: :class:`str`
        :param path: url path
        :type  msg_type: :class:`str`
        :param msg_type: transport msg type
        :type  protocol_handler: :class:`vmware.vapi.protocol.server.transport.\
            async_protocol_handler.AsyncProtocolHandler`
        :param protocol_handler: protocol handler for this path
        :rtype: :class:`bool`
        :return: True if added. False otherwise
        """
        content_type = self.HTTP_CONTENT_MAPPING.get(msg_type)
        if content_type is None:
            logger.error('Unsupported msg type: %s', msg_type)
            return False

        paths = [token for token in path.split('/') if token]
        if len(paths) == 0:
            logger.error('Cannot register root resource: %s', path)
            return False

        curr_resources = self.root_resource
        for node in paths[:-1]:
            node = node.encode('utf-8')
            node_entity = curr_resources.getStaticEntity(node)
            if node_entity:
                curr_resources = node_entity
            else:
                logger.debug('Adding child node %s', node)
                node_entity = Resource()
                curr_resources.putChild(node, node_entity)
                curr_resources = node_entity

        node = paths[-1].encode('utf-8')
        leave_entity = curr_resources.getStaticEntity(node)
        if isinstance(leave_entity, TwistedVapiResource):
            vapi_resource = leave_entity
        else:
            vapi_resource = TwistedVapiResource()
        if not vapi_resource.add_handler(content_type, protocol_handler):
            logger.error('Cannot re-register resource @ %s', path)
            return False
        logger.debug('Adding child node %s', node)
        curr_resources.putChild(node, vapi_resource)
        return True


class TwistedServer(ServerInterface):
    """ Twisted server """

    SUPPORTED_SCHEMES = ('vmware', 'vmwares', 'http', 'https')

    def __init__(self):
        """ Twisted server init """
        ServerInterface.__init__(self)
        self.lock = threading.Lock()
        self.handlers_map = {}

        # Protocol factories
        self.protocol_factories = {}

        self.main_thread_only = True

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
        # addr is url
        scheme, host, port, _, _, path, _ = parse_addr_url(addr)
        # https / vmwares
        if scheme not in self.SUPPORTED_SCHEMES:
            logger.error('Unsupported url scheme: %s', addr)
            return

        # Get ssl context
        ssl_context = None
        if scheme == 'https' or scheme == 'vmwares':
            ssl_context = self.get_ssl_context(ssl_args)

        with self.lock:
            if scheme == 'http' or scheme == 'https':
                protocol_factory = self.protocol_factories.get((host, port))
                if not protocol_factory:
                    protocol_factory = TwistedHttpSite()
                    self.protocol_factories[(host, port)] = protocol_factory

                if not protocol_factory.add_res_handler(
                        path, msg_type, protocol_handler):
                    logger.error('Failed to add resource handler: %s', addr)
                    return
            elif scheme == 'vmware' or scheme == 'vmwares':
                protocol_factory = TwistedVmwareProtocolFactory(
                    protocol_handler)
            else:
                raise ValueError("Scheme %s is not supported" % scheme)

            self.handlers_map[(host, port)] = (protocol_factory, ssl_context)

    def get_ssl_context(self, ssl_args):
        """
        get ssl context

        :type  ssl_args: :class:`dict`
        :param ssl_args: ssl arguments
        :rtype: :class:`twisted.internet.ssl.DefaultOpenSSLContextFactory`
        :return: twisted ssl context factory instance
        """
        ssl_context = None
        ssl_ctx_args = {}
        if ssl_args:
            # Twisted don't support ca certs
            if ssl_args.get('keyfile', None):
                ssl_ctx_args['privateKeyFileName'] = ssl_args['keyfile']
            if ssl_args.get('certfile', None):
                ssl_ctx_args['certificateFileName'] = ssl_args['certfile']

        if len(ssl_ctx_args) > 0:
            logger.debug('ssl_ctx_args: %s', ssl_ctx_args)
            try:
                ssl_context = twisted.internet.ssl.DefaultOpenSSLContextFactory(
                    **ssl_ctx_args)
            except Exception:
                # Twisted without ssl support. Missing pyOpenSSL?
                logger.error('Twisted without ssl support. Missing pyOpenSSL?')
                raise
        else:
            logger.warning('Missing SSL context!')
        return ssl_context

    def serve_forever(self):
        """
        Server loop

        Note: Twisted limitation: Must be running from main thread
        """
        with self.lock:
            if len(self.handlers_map) == 0:
                logger.info('No handler registered. Server stopped')
                return

            for info, (protocol_factory, ssl_context) in six.iteritems(
                    self.handlers_map):
                host, port = info
                host = host if host else ''
                # isIPv6Address in twisted returns False if the addr has []
                # So, removing it from the addr.
                if host.startswith('[') and host.endswith(']'):
                    host = host[1:-1]
                logger.info('Listening on: %s %s', info, ssl_context)

                # interface='', listens on only IPv4 address
                # interface='::', listens on both IPv4 and IPv6 address
                # interface='<IPv4_addr>', listen on only IPv4 address
                # interface='<IPv6_addr>', listen on only IPv6 address
                if ssl_context:
                    twisted.internet.reactor.listenSSL(port,  # pylint: disable=E1101
                                                       protocol_factory,
                                                       ssl_context,
                                                       interface=host)
                else:
                    twisted.internet.reactor.listenTCP(port, protocol_factory,  # pylint: disable=E1101
                                                       interface=host)

        logger.info('twisted internet reactor started...')
        twisted.internet.reactor.run()  # pylint: disable=E1101
        logger.info('twisted internet reactor stopped')

    def shutdown(self):
        """ Server shutdown """

        try:
            twisted.internet.reactor.stop()  # pylint: disable=E1101
        except Exception:
            # Ignore all shutdown exceptions
            pass


def get_server():
    """
    Get twisted server

    :rtype: :class:`vmware.vapi.server.server_interface.ServerInterface`
    :return: subclass of ServerInterface
    """

    args = tuple()
    kwargs = {}

    # Twisted server MUST be singleton
    global _twisted_server  # pylint: disable=W0603
    with _server_lock:
        if not _twisted_server:
            _twisted_server = TwistedServer(*args, **kwargs)
        else:
            logger.warning(
                'Twisted server is singleton. This might not be what u wanted')
        server = _twisted_server
    return server
