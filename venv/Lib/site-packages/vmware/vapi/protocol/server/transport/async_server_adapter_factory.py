#!/usr/bin/env python

"""
Async server adapter factory
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015, 2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

from vmware.vapi.lib.load import dynamic_import


class AsyncServerAdapterFactory(object):
    """ async server adapter factory """
    def __init__(self):
        """ async server adapter factory init """
        self.adapters = {
           # adapter name : constructor / constructor name
           'http': 'vmware.vapi.protocol.server.transport.msg_handler.MsgBasedProtocolHandler',
           'https': 'vmware.vapi.protocol.server.transport.msg_handler.MsgBasedProtocolHandler',
        }

    def get_adapter(self, server_adapter_name, *args, **kwargs):
        """
        get async server adapter

        :type  server_adapter_name: :class:`str`
        :param server_adapter_name: server adapter name
        :type    args: :class:`tuple`
        :param   args: position parameters to server adapter
        :type    kwargs: :class:`dict`
        :param   kwargs: key parameters to server adapter
        :rtype:  :class:`vmware.vapi.protocol.server.transport.\
                                async_protocol_handler.AsyncProtocolHandler`
        :return: Async server adapter
        """
        constructor = self.adapters.get(server_adapter_name)
        if constructor is not None:
            constructor = dynamic_import(constructor)
            if constructor:
                return constructor(*args, **kwargs)
