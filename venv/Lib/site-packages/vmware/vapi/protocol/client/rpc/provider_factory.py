"""
rpc provider factory
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015, 2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

from vmware.vapi.lib.load import dynamic_import
from vmware.vapi.lib.log import get_vapi_logger

logger = get_vapi_logger(__name__)


class RpcProviderFactory(object):
    """ Rpc provider factory """
    def __init__(self):
        """ Rpc provider factory init """
        self.rpc_providers = {
            # rpc provider name : constructor / constructor name
           'http': 'vmware.vapi.protocol.client.rpc.http_provider.HttpRpcProvider',
           'https': 'vmware.vapi.protocol.client.rpc.http_provider.HttpRpcProvider',
           'requests': 'vmware.vapi.protocol.client.rpc.requests_provider.RequestsRpcProvider',
        }

    def get_rpc_provider(self, rpc_provider_name, *args, **kwargs):
        """
        Create rpc provider

        :type  rpc_provider_name:
        :param rpc_provider_name:
        :type    args: :class:`tuple`
        :param   args: position parameters to rpc provider constructor
        :type    kwargs: :class:`dict`
        :param   kwargs: key parameters to rpc provider constructor
        :rtype:  :class:`vmware.vapi.protocol.client.rpc.provider.RpcProvider`
        :return: Rpc provider object
        """
        constructor = self.rpc_providers.get(rpc_provider_name)
        if constructor is not None:
            constructor = dynamic_import(constructor)
            if constructor:
                return constructor(*args, **kwargs)
