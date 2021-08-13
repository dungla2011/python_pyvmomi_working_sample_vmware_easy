#!/usr/bin/env python

"""
Vapi server
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015-2018 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import atexit
import locale
import logging
import logging.config
import os
import sys

from six.moves import configparser

from vmware.vapi.lib.addr_url_parser import get_url_scheme
from vmware.vapi.lib.log import get_provider_wire_logger, get_vapi_logger
from vmware.vapi.l10n.constants import DEFAULT_LOCALE
from vmware.vapi.settings import config

# Note: Use logger only after configure_logging has been called!!!
logger = None

# Set english locale for vAPI server
locale.setlocale(locale.LC_ALL, DEFAULT_LOCALE)


def check_file_exists(filename):
    """
    Check if name is a file and exists

    :type  :class:`str`
    :param file name
    """
    if not os.path.exists(filename) or not os.path.isfile(filename):
        raise os.error(2, "No such file: '%s'" % filename)


def configure_logging(cfg, spec):
    """
    Configure logging using properties file

    :type  cfg: :class:`configparser.SafeConfigParser`
    :param cfg: Provider configuration
    :type  spec: :class:`str`
    :param spec: Provider configuration file name. Need this for Python versions
        older than 3.4
    """
    if config.Sections.LOGGERS in cfg.sections():
        major, minor, _, _, _ = sys.version_info
        if major == 3 and minor >= 4:
            logging.config.fileConfig(cfg, disable_existing_loggers=False)
        else:
            # SafeConfigParser instance is not accepted in fileConfig in
            # versions older than 3.4 and hence need to pass filename
            logging.config.fileConfig(spec, disable_existing_loggers=False)
    else:
        configure_default_logging = True
        if config.Sections.LOGGING in cfg.sections():
            default = cfg.get(config.Sections.LOGGING, 'default')
            if default.lower() == 'false':
                configure_default_logging = False
        if configure_default_logging:
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(logging.INFO)
            # TODO Add opId to default format once we know it is working well
            formatter = logging.Formatter(
                '%(asctime)s %(levelname)-8s %(name)-15s %(message)s')
            handler.setFormatter(formatter)

            # Configure the root logger
            root_logger = logging.getLogger()
            root_logger.setLevel(logging.INFO)
            root_logger.addHandler(handler)
    global logger
    logger = get_vapi_logger('vmware.vapi.server.vapid')


def setup_provider_chain(provider_cfg, singleton):
    """
    Setup the API Provider chain

    In the properties file, users would specify the order of ApiProviders
    For ex: InterposerProvider, ApiAggregator. In this case all incoming
    requests would first go to InterposerProvider and then forwarded to
    ApiAggregator after processing.

    This function initializes all these providers in the reverse order
    and passes the reference of n+1th provider to nth provider.

    :type  provider_cfg: :class:`vmware.vapi.settings.config.ProviderConfig`
    :param provider_cfg: Provider Configuration
    :type singleton: :class:`bool`
    :param singleton: Specify whether to create new instances of Providers or
                      use existing ones
    :rtype: :class:`list` of :class:`vmware.vapi.core.ApiProvider`
    :return: List of API Providers
    """
    # This import cannot be at the top as we need to wait for logger to get
    # initialized with right handlers
    from vmware.vapi.lib.load import dynamic_import
    singleton_providers = {
        'ApiAggregator': 'vmware.vapi.provider.aggregator.get_provider',
        'LocalProvider': 'vmware.vapi.provider.local.get_provider',
        'InterposerProvider': 'vmware.vapi.provider.interposer.get_provider',
        'AuthenticationFilter':
            'vmware.vapi.security.authentication_filter.get_provider',
        'AuthorizationFilter':
            'vmware.vapi.security.authorization_filter.get_provider',
    }

    providers = {
        'ApiAggregator': 'vmware.vapi.provider.aggregator.AggregatorProvider',
        'LocalProvider': 'vmware.vapi.provider.local.LocalProvider',
        'InterposerProvider':
            'vmware.vapi.provider.interposer.InterposerProvider',
        'AuthenticationFilter':
            'vmware.vapi.security.authentication_filter.AuthenticationFilter',
        'AuthorizationFilter':
            'vmware.vapi.security.authorization_filter.AuthorizationFilter',
    }

    provider_types = provider_cfg.get_providers()
    provider_map = singleton_providers if singleton else providers
    filter_kwargs = {} if singleton else {'provider_config': provider_cfg}

    providers = []
    for i, provider_type in enumerate(reversed(provider_types)):
        provider_name = provider_map.get(provider_type)
        if provider_name:
            provider_constructor = dynamic_import(provider_name)
            if provider_constructor is None:
                raise ImportError('Could not import %s' % provider_name)
            if i == 0:
                # TODO: Add validation to make sure that the last provider
                # can support registration of services
                provider = provider_constructor()
                provider.register_by_properties(provider_cfg)
            else:
                provider = provider_constructor(**filter_kwargs)
                provider.next_provider = providers[i - 1]
            providers.append(provider)
        else:
            logger.error('Could not load provider')
            return []
    return providers[::-1]


def _create_provider_int(spec, singleton=True):
    """
    Parse the spec and create ApiProviders

    :type  spec: :class:`str`
    :param spec: Provider configuration
    :type  singleton: :class:`bool`
    :kwarg singleton: Specify whether to create new instances of Providers or
                      use existing ones
    :rtype:  :class:`vmware.vapi.core.ApiProvider`
    :return: Api provider instance
    """
    provider_config = config.ProviderConfig(spec)

    # Configure logging
    configure_logging(provider_config.cfg, spec)
    providers = setup_provider_chain(provider_config, singleton)
    if not providers:
        return (provider_config, providers)

    if 'ENABLE_VAPI_PROVIDER_WIRE_LOGGING' in os.environ:
        get_provider_wire_logger().propagate = True
    # Get the first API Provider to connect to RPC
    provider = providers[0]
    return (provider_config, providers)


def create_provider(spec, singleton=True):
    """
    Create an ApiProvider

    :type  spec: :class:`str`
    :param spec: Provider configuration
    :type  singleton: :class:`bool`
    :kwarg singleton: Specify whether to create new instances of Providers or
                      use existing ones
    :rtype:  :class:`vmware.vapi.core.ApiProvider`
    :return: Api provider instance
    """
    _, providers = _create_provider_int(spec, singleton)
    return providers[0]


def create_servers(spec, singleton=False):
    """
    Create RPC servers

    :type  spec: :class:`str`
    :param spec: Provider configuration
    :type  singleton: :class:`bool`
    :kwarg singleton: Specify whether to create new instances of Providers or
                      use existing ones
    :rtype: :class:`list` of
        :class:`vmware.vapi.server.server_interface.ServerInterface`
    :return: list of servers
    """
    server_providers = {
        'twisted': 'vmware.vapi.server.twisted_server.get_server',
        'stdio': 'vmware.vapi.server.stdio_server.get_server',
        'wsgi': 'vmware.vapi.server.wsgi_server.get_server',
    }

    provider_cfg, providers = _create_provider_int(spec, singleton)
    provider = providers[0]

    try:
        protocol_configs = provider_cfg.get_provider_protocols()
    except configparser.NoOptionError:
        raise Exception('No protocol configurations specified')

    # These import cannot be at the top as we need to wait for logger to get
    # initialized with right handlers
    from vmware.vapi.lib.load import dynamic_import
    from vmware.vapi.protocol.server.msg.handler_factory import (
        ProtocolHandlerFactory)
    from vmware.vapi.protocol.server.transport.async_server_adapter_factory \
        import AsyncServerAdapterFactory
    servers = {}
    msg_handlers = {}
    protocol_handlers = {}
    is_wsgi = False
    for protocol_config in protocol_configs:
        url = provider_cfg.get_provider_url(protocol_config)
        logger.info('url: %s', url)

        transport_protocol = get_url_scheme(url)
        logger.info('transport protocol: %s', transport_protocol)

        # Get request handler
        msg_handler_factory = ProtocolHandlerFactory()

        # Add all pre processors
        # TODO Add these as default values in provider config instead of
        # hardcoding here
        pre_processors = ['vmware.vapi.security.sso.JSONSSOVerifier']

        msg_protocol = provider_cfg.get_provider_message_format(protocol_config)
        msg_handler = msg_handler_factory.get_handler(
            msg_protocol, provider, pre_processors)
        msg_handlers[(msg_protocol, provider)] = msg_handler

        # Get server constructor
        rpc_server = provider_cfg.get_provider_server(protocol_config)
        logger.info('rpc server: %s', rpc_server)

        # Get async server to msg handler adapter
        adapter_factory = AsyncServerAdapterFactory()
        if rpc_server in ['wsgi', 'stdio']:
            protocol_handler = msg_handler
        else:
            protocol_handler = adapter_factory.get_adapter(
                transport_protocol, msg_handler)

        # Extract ssl arguments
        ssl_args = provider_cfg.get_provider_ssl_args(protocol_config)

        # Register handler
        server = servers.get(rpc_server)
        if not server:
            server_name = server_providers.get(rpc_server)
            if server_name is not None:
                server_constructor = dynamic_import(server_name)
            if server_constructor is None:
                raise Exception('Could not find RPC constructor')

            server = server_constructor()
            if rpc_server == 'wsgi':
                server.provider_config = provider_cfg
            servers[rpc_server] = server
        server.register_handler(url, msg_protocol, protocol_handler, ssl_args)

        # Get tasks configuration
        if provider_cfg.are_tasks_enabled():
            thread_count = provider_cfg.get_provider_task_threads()
            from vmware.vapi.lib.thread_pool import get_threadpool
            thread_pool = get_threadpool(thread_count)

            task_manager = provider_cfg.get_provider_task_manager()
            task_manager_constructor = dynamic_import(task_manager)
            from vmware.vapi.task.task_manager_impl import get_task_manager
            task_manager_instance = get_task_manager(task_manager_constructor)

            priv_validator = provider_cfg.get_provider_privilege_validator()
            if priv_validator is not None:
                priv_validator_constructor = dynamic_import(priv_validator)
                from vmware.vapi.security.privilege import (
                    get_privilege_validator)
                privilege_validator_instance = get_privilege_validator(
                    priv_validator_constructor)

    return list(servers.values())


def shutdown_servers(servers):
    """
    Shutdown all servers

    :type  :class:`list` of servers
    :param List of servers to shutdown
    """
    for server in servers:
        server.shutdown()


def main():
    """ main """
    spec = sys.argv[1]
    check_file_exists(os.path.abspath(spec))

    servers = create_servers(spec)
    if len(servers) == 0:
        logger.info('No server available. Quit')
        return

    if len(servers) > 1:
        threaded_servers = []
        main_thread_server = None
        for server in servers:
            if getattr(server, 'main_thread_only', False):
                if main_thread_server is None or main_thread_server == server:
                    main_thread_server = server
                else:
                    raise Exception(
                        'More than one servers required running on '
                        + 'main thread!')
            else:
                threaded_servers.append(server)

        # Use thread pool to start servers
        from vmware.vapi.lib.thread_pool import ThreadPool
        pool = ThreadPool(max_workers=len(servers))
        atexit.register(shutdown_servers, servers)
        if main_thread_server:
            for server in threaded_servers:
                pool.queue_work(server.serve_forever)
            main_thread_server.serve_forever()
        else:
            # Wait until all server die
            pool.queue_works_and_wait(
                [server.serve_forever for server in threaded_servers])
    else:
        server = servers[0]
        server.serve_forever()


if __name__ == '__main__':
    main()
