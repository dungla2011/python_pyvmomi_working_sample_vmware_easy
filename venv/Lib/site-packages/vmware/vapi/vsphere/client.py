"""
vSphere Client
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2017 VMware, Inc.  All rights reserved.'  # pylint: disable=line-too-long

import requests

from com.vmware.cis_client import Session
from vmware.vapi.bindings.stub import ApiClient
from vmware.vapi.bindings.stub import StubFactoryBase
from vmware.vapi.lib.connect import get_requests_connector
from vmware.vapi.security.client.security_context_filter import \
    LegacySecurityContextFilter
from vmware.vapi.security.session import create_session_security_context
from vmware.vapi.security.sso import create_saml_bearer_security_context
from vmware.vapi.security.sso import create_saml_security_context
from vmware.vapi.security.user_password import \
    create_user_password_security_context
from vmware.vapi.stdlib.client.factories import StubConfigurationFactory

from com.vmware.vcenter.hvc_client import StubFactory as hvc_factory
from com.vmware.vcenter.compute_client import StubFactory as compute_factory
from com.vmware.vcenter.vm.compute_client import StubFactory as vm_compute_factory
from com.vmware.vcenter.inventory_client import StubFactory as inventory_factory
from com.vmware.vcenter.iso_client import StubFactory as iso_factory
from com.vmware.vcenter.ovf_client import StubFactory as ovf_factory
from com.vmware.vcenter.vm_template_client import StubFactory as vm_template_factory
from com.vmware.vcenter.lcm_client import StubFactory as lcm_factory
from com.vmware.appliance.recovery_client import StubFactory as appliance_recovery_factory
from com.vmware.appliance.infraprofile_client import StubFactory as appliance_infraprofile_factory
from com.vmware.appliance.vmon_client import StubFactory as appliance_vmon_factory


JSON_RPC_ENDPOINT = '/api'


class StubFactory(StubFactoryBase):

    def __init__(self, stub_config):
        StubFactoryBase.__init__(self, stub_config)
        self.vcenter.hvc = hvc_factory(stub_config)
        self.vcenter.compute = compute_factory(stub_config)
        self.vcenter.vm.compute = vm_compute_factory(stub_config)
        self.vcenter.inventory = inventory_factory(stub_config)
        self.vcenter.iso = iso_factory(stub_config)
        self.vcenter.ovf = ovf_factory(stub_config)
        self.vcenter.vm_template = vm_template_factory(stub_config)
        self.vcenter.lcm = lcm_factory(stub_config)
        self.appliance.recovery = appliance_recovery_factory(stub_config)
        self.appliance.infraprofile = appliance_infraprofile_factory(stub_config)
        self.appliance.vmon = appliance_vmon_factory(stub_config)

    _attrs = {
        'vcenter': 'com.vmware.vcenter_client.StubFactory',
        'appliance': 'com.vmware.appliance_client.StubFactory',
        'content': 'com.vmware.content_client.StubFactory',
        'tagging': 'com.vmware.cis.tagging_client.StubFactory',
    }


class VsphereClient(ApiClient):
    """
    vSphere Client class that provides access to stubs for all services in the
    vSphere API
    """

    def __init__(self, session, server, username, password, bearer_token,
                 hok_token, private_key):
        """
        Initialize VsphereClient by creating a parent stub factory instance
        of all vSphere components.

        :type  session: :class:`requests.Session`
        :param session: Requests HTTP session instance. If not specified,
        then one is automatically created and used
        :type  server: :class:`str`
        :param server: vCenter host name or IP address
        :type  username: :class:`str`
        :param username: Name of the user
        :type  password: :class:`str`
        :param password: Password of the user
        :type  bearer_token: :class:`str`
        :param bearer_token: SAML Bearer Token
        :type  hok_token: :class:`str`
        :param hok_token: SAML Hok Token
        :type  private_key: :class:`str`
        :param private_key: Absolute file path of the private key of the user
        """
        if not session:
            session = requests.Session()
        self.session = session
        host_url = "https://" + server + JSON_RPC_ENDPOINT

        if username is not None and password is not None and \
                not bearer_token and not hok_token:
            sec_ctx = create_user_password_security_context(username, password)
        elif bearer_token and not username and not hok_token:
            sec_ctx = create_saml_bearer_security_context(bearer_token)
        elif hok_token and private_key and not bearer_token and not username:
            sec_ctx = create_saml_security_context(hok_token, private_key)
        else:
            raise ValueError('Please provide exactly one of the following '
                             'authentication scheme: username/password, '
                             'bearer_token or hok_token/private_key')

        session_svc = Session(
            StubConfigurationFactory.new_std_configuration(
                get_requests_connector(
                    session=session, url=host_url,
                    provider_filter_chain=[
                        LegacySecurityContextFilter(
                            security_context=sec_ctx)])))

        session_id = session_svc.create()
        sec_ctx = create_session_security_context(session_id)
        stub_config = StubConfigurationFactory.new_std_configuration(
            get_requests_connector(
                session=session, url=host_url,
                provider_filter_chain=[
                    LegacySecurityContextFilter(
                        security_context=sec_ctx)]))
        self.session_svc = Session(stub_config)
        stub_factory = StubFactory(stub_config)
        ApiClient.__init__(self, stub_factory)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__del__()

    def __del__(self):
        try:
            self.session_svc.delete()
        except Exception:
            # Catch exceptions when terminating the vSphere session and go ahead
            # close the requests session.
            pass
        if hasattr(self, 'session'):
            self.session.close()


def create_vsphere_client(server, username=None, password=None,
                          bearer_token=None, hok_token=None, private_key=None,
                          session=None):
    """
    Helper method to create an instance of the vSphere API client.
    Please provide one of the following options to authenticate:
        * username and password,
        * bearer_token,
        * hok_token and private_key

    :type  server: :class:`str`
    :param server: vCenter host name or IP address
    :type  username: :class:`str`
    :param username: Name of the user
    :type  password: :class:`str`
    :param password: Password of the user
    :type  bearer_token: :class:`str`
    :param bearer_token: SAML Bearer Token
    :type  hok_token: :class:`str`
    :param hok_token: SAML Hok Token
    :type  private_key: :class:`str`
    :param private_key: Absolute file path of the private key of the user
    :type  session: :class:`requests.Session` or ``None``
    :param session: Requests HTTP session instance. If not specified, then one
        is automatically created and used
    :rtype: :class:`vmware.vapi.vmc.client.VsphereClient`
    :return: Vsphere Client instance
    """
    return VsphereClient(session=session, server=server, username=username,
                         password=password, bearer_token=bearer_token,
                         hok_token=hok_token, private_key=private_key)
