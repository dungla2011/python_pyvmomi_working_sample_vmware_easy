"""
Various http lib classes
"""
__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2016 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import six


class HTTPRequest(object):
    """
    This class represents an HTTP Request

    :type method: :class:`vmware.vapi.protocol.common.http_lib.HTTPMethod`
    :ivar method: The http method to be used to make the http request
    :type body: :class:`str`
    :ivar body: HTTP request body
    :type url_path: :class:`str`
    :ivar url_path: URL path that is to be appended to base URL to construct
                    final request URL
    :type headers: :class:`dict` of :class:`str`, :class:`str`
    :ivar headers: HTTP request headers
    :type cookies: :class:`dict` of :class:`str`, :class:`str`
    :ivar cookies: HTTP request cookies
    :type timeout: :class:`int`
    :ivar timeout: Timeout in seconds for the client to wait for the
                   response from the server
    """
    def __init__(self, method, body=None, url_path=None, headers=None,
                 cookies=None, timeout=None):
        """
        Initialize HTTPRequest

        :type  method: :class:`vmware.vapi.protocol.common.http_lib.HTTPMethod`
        :param method: The http method to be used to make the http request
        :type  body: :class:`str`
        :param body: HTTP request body
        :type  url_path: :class:`str`
        :param url_path: URL path that is to be appended to base URL to
            construct final request URL
        :type  headers: :class:`dict` of :class:`str`, :class:`str`
        :param headers: HTTP request headers
        :type  cookies: :class:`dict` of :class:`str`, :class:`str`
        :param cookies: HTTP request cookies
        :type  timeout: :class:`int`
        :param timeout: Timeout in seconds for the client to wait for the
                        response from the server
        """
        self.method = method
        self.url_path = url_path
        self.headers = headers
        self.body = body
        self.cookies = cookies
        self.timeout = timeout


class HTTPResponse(object):
    """
    This class represents an HTTP Response

    :type status: :class:`int`
    :ivar status: HTTP response status code
    :type headers: :class:`dict` of :class:`str`, :class:`str`
    :ivar headers: HTTP response headers
    :type body: :class:`str`
    :ivar body: HTTP response body
    :type data: :class:`object`
    :ivar data: Extra data depending on the HTTP library used
    """
    def __init__(self, status, headers, body=None, data=None):
        """
        Initialize HTTPResponse

        :type  status: :class:`int`
        :param status: HTTP response status code
        :type  headers: :class:`dict` of :class:`str`, :class:`str`
        :param headers: HTTP response headers
        :type  body: :class:`str`
        :param body: HTTP response body
        :type  data: :class:`object`
        :param body: Extra data depending on the HTTP library used
        """
        self.status = status
        self.headers = headers
        self.body = body
        self.data = data


class HTTPMethod(six.text_type):
    """
    Enum representing the HTTP method
    """
    DELETE = None
    GET = None
    HEAD = None
    OPTIONS = None
    PATCH = None
    POST = None
    PUT = None

HTTPMethod.DELETE = HTTPMethod('DELETE')
HTTPMethod.GET = HTTPMethod('GET')
HTTPMethod.HEAD = HTTPMethod('HEAD')
HTTPMethod.OPTIONS = HTTPMethod('OPTIONS')
HTTPMethod.PATCH = HTTPMethod('PATCH')
HTTPMethod.POST = HTTPMethod('POST')
HTTPMethod.PUT = HTTPMethod('PUT')
