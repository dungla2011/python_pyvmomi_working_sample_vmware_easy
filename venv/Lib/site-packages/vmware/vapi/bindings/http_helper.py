"""
Rest http helper methods
"""
__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2019 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

from vmware.vapi.lib.log import get_vapi_logger

logger = get_vapi_logger(__name__)


class ResponseExtractor(object):

    """
    Http response extractor utility classes
    """
    def __init__(self):
        """
        Initialize the response extractor
        """
        self._response_status = None
        self._response_headers = None
        self._response_body = None
        self._method = None
        self._url = None

    def set_http_status(self, status):
        """
        Set http response status

        :type  status: :class:`str`
        :param status: Http status
        """
        self._response_status = status

    def get_http_status(self):
        """
        Get http response status

        :rtype: :class:`str`
        :return: Http response status
        """
        return self._response_status

    def set_http_headers(self, headers):
        """
        Set http response headers

        :type  headers: :class:`dict` of :class:`str`, :class:`str`
        :param headers: Http response headers
        """
        self._response_headers = headers

    def get_http_headers(self):
        """
        Get http response headers

        :rtype: :class:`dict` of :class:`str`, :class:`str`
        :return: Http response headers
        """
        return self._response_headers

    def set_http_body(self, body):
        """
        Set http response body

        :type  body: :class:`str`
        :param body: Http body object
        """
        self._response_body = body

    def get_http_body(self):
        """
        Get http response body

        :rtype: :class:`str`
        :return: Http response body
        """
        return self._response_body

    def set_http_method(self, method):
        """
        Set http request method

        :type  method: :class:`vmware.vapi.protocol.common.http_lib.HttpMethod`
        :param method: Http request method
        """
        self._method = method

    def get_http_method(self):
        """
        Get http request method

        :rtype: :class:`vmware.vapi.protocol.common.http_lib.HttpMethod`
        :return: Http request method
        """
        return self._method

    def set_http_url(self, url):
        """
        Set http request URL

        :type  url: :str`
        :param url: Http request url
        """
        self._url = url

    def get_http_url(self):
        """
        Get http request url

        :rtype: :class:`str`
        :return: Http request url
        """
        return self._url
