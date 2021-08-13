#!/usr/bin/env python

"""
Async protocol handler interface
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long


# Interface class, don't need to warn about unused argument / method
# could be function, or abstracted class not referenced
# pylint: disable=W0613,R0201
class AsyncProtocolHandler(object):
    """ Async protocol handler """

    def __init__(self):
        """ Async protocol handler init """
        pass

    class DataHandler(object):
        """ Async protocol data handler """
        def __init__(self):
            """ Async protocol data handler init """
            pass

        def data_ready(self, data):
            """
            Callback when data arrived

            :type  data: :class:`str`
            :param data: data arrived
            """
            raise NotImplementedError

        def data_end(self):
            """ Callback when connection was closed """
            raise NotImplementedError

        def data_abort(self):
            """ Callback when connection was aborted """
            raise NotImplementedError

        def can_read(self):
            """
            Used to throttle the lower layer from sending more data

            :rtype:  :class:`bool`
            :return: True if can accept data. False otherwise
            """
            return True

    def get_data_handler(self, connection):
        """
        get data handler

        connection must support the follow:
        write(data) : function : write data
        flush() : function : flush data
        close() : function : close the connection

        :type  connection: :class:`file`
        :param connection: connection
        :rtype: :class:`AsyncProtocolHandler.DataHandler`
        :return: A logical data handler for this connection
        """
        raise NotImplementedError
