"""
vAPI Connection factory
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015, 2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import os
import warnings

from vmware.vapi.lib.ssl import UnverifiedClientContextFactory
from vmware.vapi.protocol.client.rpc.provider_factory import RpcProviderFactory
from vmware.vapi.protocol.client.msg.connector_factory import (
    ProtocolConnectorFactory)

REQUESTS_RPC_PROVIDER_NAME = 'requests'


def check_file_exists(filename):
    """
    Check if name is a file and exists

    :type  :class:`str`
    :param file name
    """
    if not os.path.isfile(filename):
        raise OSError(2, 'No such file', filename)


def get_connector(rpc_provider_name, msg_protocol, ssl_context=None, **kwargs):
    """
    Create a connection to the vAPI Provider using the specified arguments

    :type  rpc_provider_name: :class:`str`
    :param rpc_provider_name: The RPC provider to be used for the connection.
                              Valid values are 'http', 'https' and 'requests'
    :type  msg_protocol: :class:`str`
    :param msg_protocol: The message protocol to be used for the connection.
                         Valid values are 'json'.
    :type  ssl_context: :class:`OpenSSL.SSL.Context`
    :param ssl_context: SSL context to use for SSL connections
    :param kwargs: Additional arguments for the RPC provider

    :rtype:  :class:`vmware.vapi.protocol.client.connector.Connector`
    :return: Connection to the vAPI provider
    """
    warnings.warn("This function is deprecated. Please use \
                  get_requests_connector instead.",
                  DeprecationWarning)
    return _get_connector(
        rpc_provider_name, msg_protocol, ssl_context, **kwargs)


def _get_connector(rpc_provider_name, msg_protocol, ssl_context=None, **kwargs):
    """
    Create a connection to the vAPI Provider using the specified arguments

    :type  rpc_provider_name: :class:`str`
    :param rpc_provider_name: The RPC provider to be used for the connection.
                              Valid values are 'http', 'https' and 'requests'
    :type  msg_protocol: :class:`str`
    :param msg_protocol: The message protocol to be used for the connection.
                         Valid values are 'json'.
    :type  ssl_context: :class:`OpenSSL.SSL.Context`
    :param ssl_context: SSL context to use for SSL connections
    :param kwargs: Additional arguments for the RPC provider

    :rtype:  :class:`vmware.vapi.protocol.client.connector.Connector`
    :return: Connection to the vAPI provider
    """
    #RPC provider
    rpc_provider_args = {}

    if rpc_provider_name in ('http', 'https'):
        # provider url
        rpc_provider_args['url'] = kwargs.get('url')
        if rpc_provider_name == 'http' and not ssl_context:
            # In case of http, use an unverified context. This is a temporary
            # hack to not break clients who pass an https url for an http
            # connector since we now verify server cert by default. Once all the
            # clients move off to using requests, this block can be deleted.
            ssl_context = UnverifiedClientContextFactory().get_context()
        rpc_provider_args['ssl_args'] = {'ssl_context': ssl_context}
    elif rpc_provider_name in ('requests'):
        for arg_name in ('session', 'pool_size'):
            rpc_provider_args[arg_name] = kwargs.get(arg_name)
        rpc_provider_args['base_url'] = kwargs.get('url')
        rpc_provider_args['default_timeout'] = kwargs.get('timeout')
    else:
        raise Exception('Invalid RPC Provider specified %s' % rpc_provider_name)

    rpc_factory = RpcProviderFactory()
    rpc_provider = rpc_factory.get_rpc_provider(rpc_provider_name,
                                                **rpc_provider_args)

    # Add all the post processors
    post_processors = ['vmware.vapi.security.sso.JSONSSOSigner']
    provider_filter_chain = kwargs.get('provider_filter_chain')

    # Msg protocol provider
    connector_factory = ProtocolConnectorFactory()
    connector = connector_factory.get_connector(
        msg_protocol, rpc_provider, post_processors, provider_filter_chain)

    return connector


def get_saml_hok_connector(rpc_provider_name, msg_protocol='json',
                           ssl_context=None, **kwargs):
    """
    Create a connection that uses SAML Hok based authentication
    to connect to a vAPI Provider

    :type  rpc_provider_name: :class:`str`
    :param rpc_provider_name: The RPC provider to be used for the connection.
                              Valid values are 'http', 'https' or 'requests'
    :type  msg_protocol: :class:`str`
    :param msg_protocol: The message protocol to be used for the connection.
                         Valid values are 'json'.
    :type  ssl_context: :class:`OpenSSL.SSL.Context`
    :param ssl_context: SSL context to use for SSL connections
    :type  kwargs: :class:`dict` of :class:`str` and :class:`object`
    :param kwargs: Additional arguments for the RPC provider

    :rtype:  :class:`vmware.vapi.protocol.client.connector.Connector`
    :return: Connection to the vAPI provider
    """
    warnings.warn("This function is deprecated. Please use \
                  get_requests_connector instead.",
                  DeprecationWarning)
    return _get_connector(rpc_provider_name, msg_protocol, ssl_context,
                          **kwargs)


def get_requests_connector(
        session, msg_protocol='json', url=None, timeout=None, pool_size=8,
        provider_filter_chain=None):
    """
    Create a connection that uses 'requests' library for http(s) connections to
    a vAPI Provider.

    :type  session: :class:`requests.Session`
    :param session: Session object
    :type  msg_protocol: :class:`str`
    :param msg_protocol: Message protocol to be used for the connection. Valid
        values are 'json'.
    :type  url: :class:`str`
    :param url: HTTP(S) URL to be used
    :type  timeout: :class:`int`
    :param timeout: Request timeout
    :type  pool_size: :class:`int`
    :param pool_size: Connection pool size to be used
    :type  provider_filter_chain: :class:`list` of
        :class:`vmware.vapi.provider.filter.ApiProviderFilter`
    :param provider_filter_chain: List of API filters in order they are to be
        chained
    :rtype: :class:`vmware.vapi.protocol.client.connector.Connector`
    :return: Connection to the vAPI provider
    """
    return _get_connector(
        REQUESTS_RPC_PROVIDER_NAME, msg_protocol, url=url, session=session,
        timeout=timeout, pool_size=pool_size,
        provider_filter_chain=provider_filter_chain)


def get_requests_hok_connector(session, msg_protocol='json', url=None,
                               timeout=None, pool_size=8):
    """
    Create a connection that uses SAML Hok based authentication using 'requests'
    library to connect to a vAPI Provider.

    :type  session: :class:`requests.Session`
    :param session: Session object
    :type  msg_protocol: :class:`str`
    :param msg_protocol: Message protocol to be used for the connection. Valid
        values are 'json'.
    :type  url: :class:`str`
    :param url: HTTP(S) URL to be used
    :type  timeout: :class:`int`
    :param timeout: Request timeout
    :type  pool_size: :class:`int`
    :param pool_size: Connection pool size to be used
    :rtype: :class:`vmware.vapi.protocol.client.connector.Connector`
    :return: Connection to the vAPI provider
    """
    warnings.warn("This function is deprecated. Please use \
                  get_requests_connector instead.",
                  DeprecationWarning)
    return _get_connector(REQUESTS_RPC_PROVIDER_NAME, msg_protocol, url=url,
                          session=session, timeout=timeout, pool_size=pool_size)
