"""
Protocol connector factory
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015, 2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

from vmware.vapi.lib.load import dynamic_import
from vmware.vapi.lib.log import get_vapi_logger

logger = get_vapi_logger(__name__)


class ProtocolConnectorFactory(object):
    """ Protocol connector factory """

    def __init__(self):
        """ Protocol connector factory init """
        self.connectors = {
             # msg protocol name : constructor
            'json': 'vmware.vapi.protocol.client.msg.json_connector.get_protocol_connector',
            'rest': 'vmware.vapi.protocol.client.msg.rest_connector.get_protocol_connector',
        }

    def get_connector(self, protocol, *args, **kwargs):
        """
        Create protocol connector

        :type    protocol: :class:`str`
        :param   protocol: protocol name
        :type    args: :class:`tuple`
        :param   args: position parameters to protocol connector constructor
        :type    kwargs: :class:`dict`
        :param   kwargs: key parameters to protocol connector constructor
        :rtype:  :class:`vmware.vapi.protocol.client.connector.Connector`
        :return: Connector object
        """
        constructor = self.connectors.get(protocol)
        if constructor is not None:
            constructor = dynamic_import(constructor)
            if constructor:
                return constructor(*args, **kwargs)
