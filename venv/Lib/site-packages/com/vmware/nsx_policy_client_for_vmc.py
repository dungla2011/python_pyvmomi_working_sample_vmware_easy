# *********************************************************************
# Copyright 2018 VMware, Inc.  All rights reserved. VMware Confidential
# *********************************************************************

"""
Convenience methods to get API clients for NSX APIs in VMC
"""
import requests

from com.vmware import nsx_policy_client
from vmware.vapi.bindings.stub import ApiClient
from vmware.vapi.lib.connect import get_requests_connector
from vmware.vapi.security.client.security_context_filter import (
    SecurityContextFilter)
from vmware.vapi.security.oauth import create_oauth_security_context
from vmware.vapi.stdlib.client.factories import StubConfigurationFactory

__author__ = 'VMware, Inc.'
__copyright__ = ('Copyright 2018 VMware, Inc.  All rights reserved. '
                 '-- VMware Confidential')  # pylint: disable=line-too-long


"""
CSP Refresh token based SecurityContextFilter
"""


class CSPSecurityContextFilter(SecurityContextFilter):
    """
    CSP Security Context filter in API Provider chain adds the security
    context based on a refresh token to the execution context passed in.
    """

    def __init__(self, session, refresh_token, refresh_url):
        """
        Initialize SecurityContextFilter

        :type  session: :class:`requests.Session`
        :param session: Requests Session object to use for making HTTP calls
        :type  refresh_token: :class:`str`
        :param refresh_token: Refresh token to use for obtaining an access
            token
        :type  refresh_url: :class:`str`
        :param refresh_url: URL that allows exchanging a refresh token for an
            access token
        """
        SecurityContextFilter.__init__(self, None)
        self._session = session
        self._refresh_token = refresh_token
        self._data = {'refresh_token': refresh_token}
        self._refresh_url = refresh_url
        self._access_token = None

    def get_max_retries(self):
        """
        Get the max number of retries

        :rtype: :class:`int`
        :return: Number of retries
        """
        return 1

    def get_security_context(self, on_error):
        """
        Retrieve security context. If this method is called after an error
        occured, then a new access token is obtained using the refresh
        token and a new security context is created.

        :type  on_error: :class:`bool`
        :param on_error: Whether this method is called after getting an error
        :rtype: :class:`vmware.vapi.core.SecurityContext`
        :return: Security context
        """
        if on_error or not self._access_token:
            token = self._session.post(
                self._refresh_url, data=self._data).json()
            self._access_token = token['access_token']
        return create_oauth_security_context(self._access_token)

    def should_retry(self, error_value):
        """
        Returns whether the request should be retried or not based on the error
        specified.

        :type  error_value: :class:`vmware.vapi.data.value.ErrorValue`
        :param error_value: Method error
        :rtype: :class:`bool`
        :return: Returns True if request should be retried in case the error is
            either Unauthenticated or Unauthorized else False
        """
        if error_value and error_value.name in [
                'com.vmware.vapi.std.errors.unauthenticated',
                'com.vmware.vapi.std.errors.unauthorized']:
            return True
        return False


PUBLIC_VMC_URL = 'https://vmc.vmware.com/'
PUBLIC_CSP_URL = 'https://console.cloud.vmware.com'


class VmcNsxClient(ApiClient):
    """
    Client class that providess access to stubs for all the services in the
    VMC NSX API
    """
    _CSP_REFRESH_URL_SUFFIX = '/csp/gateway/am/api/auth/api-tokens/authorize'

    def __init__(self, stub_factory_class, session, refresh_token,
                 vmc_url, csp_url, org_id, sddc_id):
        """
        Initialize VmcClient by creating a stub factory instance using a CSP
        Security context filter added to the filter chain of the connector

        :type  stub_factory_class: :class:`type`
        :param stub_factory_class: Which stub factory class to use
        :type  session: :class:`requests.Session`
        :param session: Requests HTTP session instance
        :type  refresh_token: :class:`str`
        :param refresh_token: Refresh token obtained from CSP
        :type  vmc_url: :class:`str`
        :param vmc_url: URL of the VMC service
        :type  csp_url: :class:`str`
        :param csp_url: URL of the CSP service
        :type  org_id: :class:`str`
        :param org_id: ID of the VMC organization
        :type  sddc_id: :class:`str`
        :param sddc_id: ID of the VMC Software-Defined Data Center (SDDC)
        """
        # Call the VMC API to obtain the URL for the NSX Reverse Proxy
        refresh_url = "%s/%s" % (csp_url, self._CSP_REFRESH_URL_SUFFIX)
        resp = requests.post(
            "%s?refresh_token=%s" % (refresh_url, refresh_token))
        resp.raise_for_status()
        resp_json = resp.json()
        access_token = resp_json["access_token"]
        v_session = requests.Session()
        v_session.headers["csp-auth-token"] = access_token
        sddc_url = "%svmc/api/orgs/%s/sddcs/%s" % (vmc_url, org_id, sddc_id)
        resp = v_session.get(sddc_url)
        resp.raise_for_status()
        resp_json = resp.json()
        nsx_url = resp_json.get(
            "resource_config", {}).get("nsx_api_public_endpoint_url")
        # Strip trailing "/" if present
        if nsx_url and nsx_url[-1] == "/":
            nsx_url = nsx_url[:-1]

        # Create the stub factory for the NSX API
        stub_factory = stub_factory_class(
            StubConfigurationFactory.new_std_configuration(
                get_requests_connector(
                    session=session, msg_protocol='rest', url=nsx_url,
                    provider_filter_chain=[
                        CSPSecurityContextFilter(
                            session, refresh_token, refresh_url)])))
        ApiClient.__init__(self, stub_factory)


def create_nsx_policy_client_for_vmc(refresh_token, org_id, sddc_id,
                                     session=None):
    """
    Helper method to create an instance of the VMC NSX Policy API client

    :type  refresh_token: :class:`str`
    :param refresh_token: Refresh token obtained from CSP
    :type  org_id: :class:`str`
    :param org_id: ID of the VMC organization
    :type  sddc_id: :class:`str`
    :param sddc_id: ID of the VMC Software-Defined Data Center (SDDC)
    :type  session: :class:`requests.Session` or ``None``
    :param session: Requests HTTP session instance. If not specified, then one
        is automatically created and used
    :rtype: :class:`vmware.vapi.vmc.client.VmcNsxClient`
    :return: VMC NSX Client instance
    """
    session = session or requests.Session()
    return VmcNsxClient(
        stub_factory_class=nsx_policy_client.StubFactory, session=session,
        refresh_token=refresh_token, vmc_url=PUBLIC_VMC_URL,
        csp_url=PUBLIC_CSP_URL, org_id=org_id, sddc_id=sddc_id)
