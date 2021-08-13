"""
CSP Refresh token based SecurityContextFilter
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import requests

from com.vmware.vmc_client import StubFactory
from vmware.vapi.bindings.stub import ApiClient
from vmware.vapi.lib.connect import get_requests_connector
from vmware.vapi.stdlib.client.factories import StubConfigurationFactory
from com.vmware.vmc.draas_client import StubFactory as draas_factory


from .csp_filter import CSPSecurityContextFilter

PUBLIC_VMC_URL = 'https://vmc.vmware.com/'
PUBLIC_CSP_URL = 'https://console.cloud.vmware.com'

class VmcStubFactory(StubFactory):
    def __init__(self, stub_config):
        StubFactory.__init__(self, stub_config)
        self.draas = draas_factory(stub_config)


class VmcClient(ApiClient):
    """
    VMC Client class that providess access to stubs for all the services in the
    VMC API
    """
    _CSP_REFRESH_URL_SUFFIX = '/csp/gateway/am/api/auth/api-tokens/authorize'

    def __init__(self, session, refresh_token, vmc_url, csp_url):
        """
        Initialize VmcClient by creating a stub factory instance using a CSP
        Security context filter added to the filter chain of the connector

        :type  session: :class:`requests.Session`
        :param session: Requests HTTP session instance
        :type  refresh_token: :class:`str`
        :param refresh_token: Refresh token obtained from CSP
        :type  vmc_url: :class:`str`
        :param vmc_url: URL of the VMC service
        :type  csp_url: :class:`str`
        :param csp_url: URL of the CSP service
        """
        # Build Refresh URL using the CSP URL and the Refresh URL suffix
        refresh_url = csp_url.rstrip('/') + self._CSP_REFRESH_URL_SUFFIX
        stub_factory = VmcStubFactory(
            StubConfigurationFactory.new_std_configuration(
                get_requests_connector(
                    session=session, msg_protocol='rest', url=vmc_url,
                    provider_filter_chain=[
                        CSPSecurityContextFilter(
                            session, refresh_token, refresh_url)])))
        ApiClient.__init__(self, stub_factory)


def create_vmc_client(refresh_token, session=None):
    """
    Helper method to create an instance of the VMC API client using the public
    VMC and CSP URL.

    :type  refresh_token: :class:`str`
    :param refresh_token: Refresh token obtained from CSP
    :type  session: :class:`requests.Session` or ``None``
    :param session: Requests HTTP session instance. If not specified, then one
        is automatically created and used
    :rtype: :class:`vmware.vapi.vmc.client.VmcClient`
    :return: VMC Client instance
    """
    session = session or requests.Session()
    return VmcClient(
        session=session, refresh_token=refresh_token, vmc_url=PUBLIC_VMC_URL,
        csp_url=PUBLIC_CSP_URL)
