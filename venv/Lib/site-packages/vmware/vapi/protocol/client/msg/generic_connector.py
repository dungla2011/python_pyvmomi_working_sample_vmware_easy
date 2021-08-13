"""
Generic client connector
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015, 2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long


from vmware.vapi.lib.log import get_vapi_logger
from vmware.vapi.protocol.client.connector import Connector

logger = get_vapi_logger(__name__)


class GenericConnector(Connector):
    """ A generic protocol connector """

    def __init__(self, rpc_provider, api_provider, provider_filter_chain):
        """
        Generic protocol connector init

        :type  rpc_provider: :class:`vmware.vapi.protocol.client.rpc.provider
            .RpcProvider`
        :param rpc_provider: rpc provider object
        :type  api_provider: :class:`vmware.vapi.core.ApiProvider`
        :param api_provider: api provider object
        :type  provider_filter_chain: :class:`list` of
            :class:`vmware.vapi.provider.filter.ApiProviderFilter`
        :param provider_filter_chain: List of API filters in order they are to
            be chained
        """
        Connector.__init__(self, api_provider, provider_filter_chain)
        self.rpc_provider = rpc_provider

    def connect(self):
        """ rpc provider connect """
        self.rpc_provider.connect()

    def disconnect(self):
        """ rpc provider disconnect """
        self.rpc_provider.disconnect()
