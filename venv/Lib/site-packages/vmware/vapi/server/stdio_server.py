#!/usr/bin/env python

"""
STDIO server : This handles all protocol requests over stdin/out
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015, 2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import sys

from vmware.vapi.lib.log import get_vapi_logger
from vmware.vapi.server.server_interface import ServerInterface

logger = get_vapi_logger(__name__)


class StdioServer(ServerInterface):
    """ stdio server """

    def __init__(self):
        """
        Initialize the Stdio Server instance
        """
        self.protocol_handler = None
        ServerInterface.__init__(self)

    def register_handler(self, addr, msg_type, protocol_handler, ssl_args=None):
        """
        Returns the struct definition corresponding to the method's input
        parameters. The field names in the struct definition are the parameter
        names and the field values correspond to the data definition of the
        respective fields.

        :type  addr: :class:`str`
        :param addr: Url of the provider
        :type  msg_type: :class:`str`
        :param msg_type: Message Type of the provider
        :type  protocol_handler:
            :class:`vmware.vapi.protocol.server.api_handler.ApiHandler`
        :param protocol_handler: The handler for the message protocol
        :type  ssl_args: :class:`str`
        :param ssl_args: Any ssl related arguments
        """

        self.protocol_handler = protocol_handler

    def serve_forever(self):
        """
        Receives the input from the std in of the process.
        Processes the message, handles it via the protocol_handler and then
        sends the response back.
        """
        msg = sys.stdin.read()
        if msg is None:
            logger.error("No arguments passed to cgi process")
            return
        response = self.protocol_handler.handle_request(msg)
        if response is not None:
            print(response)

    def shutdown(self):
        pass


def get_server():
    """
    get stdio server

    :rtype: :class:`vmware.vapi.server.server_interface.ServerInterface`
    :return: subclass of ServerInterface
    """
    return StdioServer()
