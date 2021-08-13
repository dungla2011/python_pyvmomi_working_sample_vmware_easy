"""
Configuration management for vAPI providers
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015, 2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import os
from six.moves import configparser

from vmware.vapi.lib.log import get_vapi_logger

logger = get_vapi_logger(__name__)


class Sections(object):
    """
    Constants for different sections in the config file
    """
    ENDPOINT = 'endpoint'
    JSONRPC = 'jsonrpc'
    LOGGERS = 'loggers'
    LOGGING = 'logging'
    REST = 'rest'
    SSL = 'ssl'
    TASKS = 'tasks'
    AUTHENTICATION_FILTER = 'vmware.vapi.security.authentication_filter'
    AUTHORIZATION_FILTER = 'vmware.vapi.security.authorization_filter'


class EndpointSection(object):
    """
    Constants for keys/prefixes/suffixes in Endpoint section in config file
    """
    PROVIDER_TYPE = 'provider.type'
    PROVIDER_NAME = 'provider.name'
    INTERFACE_LIST = 'local.interfaces'
    AGGREGATOR_CHILDREN = 'aggregator.children'
    AGGREGATOR_CHILD_PREFIX = 'aggregator.child'
    PROTOCOL_PREFIX = 'protocol'
    PROTOCOL_RPC_SUFFIX = 'rpc'
    PROTOCOL_RPC_SERVER_SUFFIX = 'rpc.server'
    PROTOCOL_URL_SUFFIX = 'url'
    PROTOCOL_MSG_SUFFIX = 'msg'
    PROTOCOL_SSL_SUFFIX = 'ssl'


class TasksSection(object):
    """
    Constants for keys/prefixes/suffixes in Tasks section in config file
    """
    THREADS = 'threads'
    TASK_MANAGER = 'task_manager'
    PRIVILEGE_VALIDATOR = 'privilege_validator'


def check_file_exists(filename):
    """
    Check if name is a file and exists

    :type  :class:`str`
    :param file name
    """
    if not os.path.exists(filename) or not os.path.isfile(filename):
        raise os.error(2, "No such file: '%s'" % filename)


class ProviderConfig(object):
    """
    Provider Configuration class that provides methods for configuring different
    aspects of the VAPI Server
    """
    def __init__(self, config_file=None):
        """
        Initialize ProviderConfig

        :type  config_file: :class:`str`
        :param config_file: Path of the config file
        """
        self.cfg = None
        if config_file:
            check_file_exists(config_file)
            self.cfg = configparser.SafeConfigParser()
            self.cfg.read(config_file)

    def _get_value(self, section_name, option_name, default_value=None):
        """
        Get the configuration value for the given section and option.

        :type  section_name: :class:`str`
        :param section_name: Name of the section in the configuration file.
        :type  option_name: :class:`str`
        :param option_name: Name of the option in the configuration file.
        :type  default_value: :class:`object`
        :param default_value: Default value to be returned if section or option
            is not present in the configuration.
        :rtype: :class:`str`
        :return: String value for the key. If the section or option is not
            present, the operation will return the default value provided
        """
        if self.cfg.has_section(section_name) and self.cfg.has_option(
                section_name, option_name):
            return self.cfg.get(section_name, option_name)
        else:
            return default_value

    def _parse_list(self, list_val):
        """
        Get list of parsed strings stripped off the delimiters and whitespaces

        :type  list_val: :class:`str`
        :param list_val: Comma separated string possibly containing delimiters
        :rtype: :class:`list` of :class:`str`
        :return: List of names of session login methods
        """
        return_val = []
        if list_val is not None:
            if ',' in list_val:
                return_val = \
                    list_val.replace('\n', '').replace('\\', '').split(',')
                return_val = [r.strip() for r in return_val]
            else:
                return_val = [list_val.strip()]
        return return_val

    def get_providers(self):
        """
        Get provider chain

        :rtype: :class:`list` of :class:`str`
        :return: List of providers in a chain
        """
        providers = self._get_value(
            Sections.ENDPOINT, EndpointSection.PROVIDER_TYPE)
        if providers:
            return self._parse_list(providers)
        return []

    def get_provider_name(self):
        """
        Get provider name

        :rtype: :class:`str`
        :return: Name of the provider key used in the config file
        """
        return self._get_value(
            Sections.ENDPOINT, EndpointSection.PROVIDER_NAME)

    def get_provider_protocols(self):
        """
        Get protol names

        :rtype: :class:`list` of :class:`str`
        :return: List of protocol names
        """
        return self._get_value(
            Sections.ENDPOINT, EndpointSection.PROTOCOL_PREFIX).split(',')

    def get_provider_url(self, protocol):
        """
        Get provider URL

        :type  protocol: :class:`str`
        :param protocol: Protocol key name
        :rtype: :class:`str` or :class:`None`
        :return: Provider URL
        """
        rpc_key = '%s.%s.%s' % (
            EndpointSection.PROTOCOL_PREFIX, protocol,
            EndpointSection.PROTOCOL_RPC_SUFFIX)
        url = self._get_value(Sections.ENDPOINT, rpc_key)
        if url == 'wsgi':
            url_key = '%s.%s.%s' % (
                EndpointSection.PROTOCOL_PREFIX, protocol,
                EndpointSection.PROTOCOL_URL_SUFFIX)
            url = self._get_value(Sections.ENDPOINT, url_key)
        return url

    def get_provider_ssl_args(self, protocol):
        """
        Extract the ssl arguments

        :type  cfg: :class:`configparser.SafeConfigParser`
        :param cfg: Configuration
        :type  protocol_prefix: :class:`str`
        :param protocol_prefix: Prefix of the protocol configuration
        :rtype: :class:`dict`
        :return: SSL arguments for this protocol configuration
        """
        ssl_args = {}

        # Try to get the certdir from environment variable or .certdir option
        certdir = os.environ.get('CERTDIR')
        if certdir is None:
            try:
                certdir_key = '%s.%s.%s.certdir' % (
                    EndpointSection.PROTOCOL_PREFIX, protocol,
                    EndpointSection.PROTOCOL_SSL_SUFFIX)
                certdir = self._get_value(Sections.ENDPOINT, certdir_key)
            except configparser.NoOptionError:
                # But don't complain yet
                pass

        for ssl_key in ('ca_certs', 'certfile', 'keyfile'):
            option = '%s.%s.%s.%s' % (
                EndpointSection.PROTOCOL_PREFIX, protocol,
                EndpointSection.PROTOCOL_SSL_SUFFIX, ssl_key)
            file_name = None
            try:
                file_name = self._get_value(Sections.ENDPOINT, option)
            except configparser.NoOptionError:
                # ca_certs, certfile and keyfile are optional, so don't complain
                # if they are not present
                pass

            if file_name is not None:
                if certdir is None:
                    # If one of ca_certs, certfile, keyfile is specified
                    # and certdir is not specified, then raise an error
                    logger.error('Specify certificate absolute directory path '
                                 'either by setting environment variable '
                                 'CERTDIR or by setting %s.certdir in the '
                                 'properties file',
                                 EndpointSection.PROTOCOL_SSL_SUFFIX)
                    raise configparser.NoOptionError(
                        '%s.certdir' % EndpointSection.PROTOCOL_SSL_SUFFIX,
                        Sections.ENDPOINT)
                else:
                    file_path = os.path.join(certdir, file_name)
                    check_file_exists(file_path)
                    ssl_args[ssl_key] = file_path
        return ssl_args

    def get_provider_server(self, protocol):
        """
        Get http server type

        :type  protocol: :class:`str`
        :param protocol: Protocol key name
        :rtype: :class:`str` or :class:`None`
        :return: Server type
        """
        server_key = '%s.%s.%s' % (
            EndpointSection.PROTOCOL_PREFIX, protocol,
            EndpointSection.PROTOCOL_RPC_SERVER_SUFFIX)
        return self._get_value(Sections.ENDPOINT, server_key)

    def get_provider_message_format(self, protocol):
        """
        Get provider message format

        :type  protocol: :class:`str`
        :param protocol: Protocol key name
        :rtype: :class:`str` or :class:`None`
        :return: Message format for the provider
        """
        msg_key = '%s.%s.%s' % (
            EndpointSection.PROTOCOL_PREFIX, protocol,
            EndpointSection.PROTOCOL_MSG_SUFFIX)
        return self._get_value(Sections.ENDPOINT, msg_key)

    def get_jsonrpc_prefix(self):
        """
        Get JSONRPC prefix

        :rtype: :class:`str`
        :return: JSONRPC prefix
        """
        return self._get_value(Sections.JSONRPC, 'prefix')

    def get_rest_prefix(self):
        """
        Get REST prefix

        :rtype: :class:`str`
        :return: REST prefix
        """
        return self._get_value(Sections.REST, 'prefix')

    def enable_rest(self):
        """
        Whether REST is to be enabled

        :rtype: :class:`bool`
        :return: Whether REST is to be enabled
        """
        return self.cfg.has_section(Sections.REST)

    def are_cookies_supported(self):
        """
        Whether cookies are to be enabled

        :rtype: :class:`bool`
        :return: Whether cookies are to be enabled
        """
        if self.cfg.has_option(Sections.REST, 'allow_cookies'):
            return self.cfg.getboolean(Sections.REST, 'allow_cookies')
        return True

    def get_rest_security_parsers(self):
        """
        Get REST security parsers

        :rtype: :class:`list` of :class:`str`
        :return: List of security parsers for REST
        """
        parsers = self._get_value(Sections.REST, 'security_parsers')
        return self._parse_list(parsers)

    def get_rest_session_methods(self):
        """
        Get REST session methods

        :rtype: :class:`list` of :class:`str`
        :return: List of names of session login methods
        """
        parsers = self._get_value(Sections.REST, 'session_methods')
        return self._parse_list(parsers)

    def get_interfaces(self):
        """
        Get interfaces

        :rtype: :class:`list` of :class:`str`
        :return: List of names of interfaces
        """
        ifaces = self._get_value(
            Sections.ENDPOINT, EndpointSection.INTERFACE_LIST)
        if ifaces:
            return self._parse_list(ifaces)
        return []

    def get_service_config(self, service):
        """
        Get service configuration

        :rtype: :class:`dict`
        :return: Dictionary object containing service configuration
        """
        if self.cfg.has_section(service):
            return dict(self.cfg.items(service))
        return {}

    def are_tasks_enabled(self):
        """
        Whether Tasks are enabled

        :rtype: :class:`bool`
        :return: Whether Tasks are enabled
        """
        return self.cfg.has_section(Sections.TASKS)

    def get_provider_task_threads(self):
        """
        Get provider threads
        """
        if self.cfg.has_option(Sections.TASKS, TasksSection.THREADS):
            return self.cfg.getint(Sections.TASKS, TasksSection.THREADS)

        # Default to 3 threads for tasks operations
        # TODO: remove when simplifying provider config defaults
        return 3

    def get_provider_task_manager(self):
        """
        Get provider task manager
        """
        return self._get_value(Sections.TASKS, TasksSection.TASK_MANAGER)

    def get_provider_privilege_validator(self):
        """
        Get provider privilege validator
        """
        return self._get_value(Sections.TASKS, TasksSection.PRIVILEGE_VALIDATOR)

    def get_child_providers(self):
        """
        Get child providers

        :rtype: :class:`list` of :class:`str`
        :return: List of names of child providers
        """
        child_providers = self._get_value(
            Sections.ENDPOINT, EndpointSection.AGGREGATOR_CHILDREN)
        if child_providers:
            return self._parse_list(child_providers)
        return []

    def get_child_url(self, child):
        """
        Get child provider URL

        :type  child: :class:`str`
        :param child: Name of the child provider key
        :rtype: :class:`str`
        :return: URL of the child provider
        """
        return self._get_value(
            Sections.ENDPOINT,
            '%s.%s.protocol.rpc' % (
                EndpointSection.AGGREGATOR_CHILD_PREFIX, child))

    def get_authentication_handlers(self):
        """
        Get authentication handlers

        :rtype: :class:`list` of :class:`str`
        :return: List of authentication handlers
        """
        handlers = self._get_value(
            Sections.AUTHENTICATION_FILTER, 'handlers')
        if handlers:
            return self._parse_list(handlers)
        return []

    def get_authorization_handlers_and_files(self):
        """
        Get authorization handlers and authentication file

        :rtype: :class:`tuple` of :class:`list` of :class:`str` and :class:`str`
        :return: Tuple of list of authorization handlers and authentication file
        """
        handlers = self._get_value(
            Sections.AUTHORIZATION_FILTER, 'handlers')
        if handlers:
            files = self._get_value(Sections.AUTHORIZATION_FILTER, 'file')
            files_list = self._parse_list(files) if files else []
            return (
                self._parse_list(handlers),
                files_list)
        return ([], [])
