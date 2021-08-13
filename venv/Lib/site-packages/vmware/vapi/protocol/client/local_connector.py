"""
Local connector
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015, 2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long


from vmware.vapi.protocol.client.connector import Connector


class LocalConnector(Connector):
    """
    Protocol connection class to get direct access to ApiProvider
    instead of going over the wire
    """
    def __init__(self, api_provider, provider_filter_chain=None):
        """
        Initialize LocalConnector

        :type  api_provider: :class:`vmware.vapi.core.ApiProvider`
        :param api_provider: ApiProvider instance to be used
        :type  provider_filter_chain: :class:`list` of
            :class:`vmware.vapi.provider.filter.ApiProviderFilter`
        :param provider_filter_chain: List of API filters in order they are to
            be chained
        """
        Connector.__init__(self, api_provider, provider_filter_chain)

    def connect(self):
        """
        Create a connection. No-op for LocalConnector
        """
        pass

    def disconnect(self):
        """
        Disconnect from a connection. No-op for LocalConnector
        """
        pass


def get_local_connector(api_provider, provider_filter_chain=None):
    """
    Creates and returns a local connection for the input ApiProvider

    :type  api_provider: :class:`vmware.vapi.core.ApiProvider`
    :param api_provider: ApiProvider instance
    :type  provider_filter_chain: :class:`list` of
        :class:`vmware.vapi.provider.filter.ApiProviderFilter`
    :param provider_filter_chain: List of API filters in order they are to be
        chained
    :rtype: :class:`vmware.vapi.protocol.client.local_connector.LocalConnector`
    :return: Newly created protocol connection for the given ApiProvider
    """
    return LocalConnector(api_provider, provider_filter_chain)
