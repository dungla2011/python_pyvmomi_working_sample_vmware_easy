"""
rpc provider interface
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015-2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import abc
import six


@six.add_metaclass(abc.ABCMeta)
class RpcProvider(object):
    """ Rpc provider interface """
    @abc.abstractmethod
    def connect(self):
        """
        connect

        :rtype: :class:`vmware.vapi.protocol.client.rpc.provider.RpcProvider`
        :return: a rpc provider
        """
        pass

    @abc.abstractmethod
    def disconnect(self):
        """ disconnect """
        pass

    @abc.abstractmethod
    def do_request(self, *args, **kwargs):
        """
        Do rpc request. Each subclass must define their own params for this
        method
        """
        pass


class HTTPProvider(RpcProvider):
    """
    HTTP rpc provider interface
    """

    @abc.abstractmethod
    def do_request(self, http_request):  # pylint: disable=W0221
        """
        Make an HTTP request
        :type  http_request:
            :class:`vmware.vapi.protocol.client.http_lib.HTTPRequest`
        :param http_request: The request to be sent
        :rtype: :class:`vmware.vapi.protocol.client.http_lib.HTTPResponse`
        :return: The http response received
        """
        pass
