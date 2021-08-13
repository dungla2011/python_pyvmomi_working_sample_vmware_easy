#!/usr/bin/env python

"""
Server interface
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long


# Interface class, don't need to warn about unused argument / method
# could be function, or abstracted class not referenced
# pylint: disable=W0613,R0201
class ServerInterface(object):
    """ Server interface """

    def __init__(self):
        """ Server interface init """
        pass

    def register_handler(self, addr, msg_type, protocol_handler, ssl_args=None):
        # pylint: disable=line-too-long
        """
        Register protocol handler

        :type  addr: :class:`str`
        :param addr: addr url
        :type  msg_type: :class:`str`
        :param msg_type: protocol message type
        :type  protocol_handler: :class:`vmware.vapi.protocol.server.transport.async_protocol_handler.AsyncProtocolHandler`
        :param protocol_handler: protocol handler for this addr
        :type  ssl_args: :class:`dict`
        :param ssl_args: ssl arguments
        """
        raise NotImplementedError

    def serve_forever(self):
        """ Server loop """
        raise NotImplementedError

    def shutdown(self):
        """ Server shutdown """
        raise NotImplementedError
