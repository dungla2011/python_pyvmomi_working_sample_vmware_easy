"""
Protocol handler factory
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015, 2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

from vmware.vapi.lib.load import dynamic_import


class ProtocolHandlerFactory(object):
    """ Protocol handler factory """

    def __init__(self):
        """ Protocol handler factory init """
        self.handlers = {
            # protocol name : constructor / constructor name
            'json': 'vmware.vapi.protocol.server.msg.json_handler.get_protocol_handler',
        }

    def get_handler(self, protocol_name, *args, **kwargs):
        """
        Create protocol handler

        :type    protocol: :class:`str`
        :param   protocol: protocol name
        :type    args: :class:`tuple`
        :param   args: position parameters to protocol handler constructor
        :type    kwargs: :class:`dict`
        :param   kwargs: key parameters to protocol handler constructor
        :rtype:  :class:`vmware.vapi.protocol.server.api_handler.ApiHandler`
        :return: Api handler object
        """
        constructor = self.handlers.get(protocol_name)
        if constructor is not None:
            constructor = dynamic_import(constructor)
            if constructor:
                return constructor(*args, **kwargs)
