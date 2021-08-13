"""
Connecter interface
"""
__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015, 2017, 2019 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import abc
import six

from vmware.vapi.core import ExecutionContext, RuntimeData
from vmware.vapi.lib.context import create_default_application_context
from vmware.vapi.security.client.security_context_filter import (
    SecurityContextFilter, LegacySecurityContextFilter)


@six.add_metaclass(abc.ABCMeta)
class Connector(object):
    """ Connector interface """
    def __init__(self, api_provider, provider_filter_chain):
        """
        Connector constructor

        :type  api_provider: :class:`vmware.vapi.core.ApiProvider`
        :param api_provider: API Provider
        :type  provider_filter_chain: :class:`list` of
            :class:`vmware.vapi.provider.filter.ApiProviderFilter`
        :param provider_filter_chain: List of API filters in order they are to
            be chained
        """
        provider_chain = provider_filter_chain[:] if provider_filter_chain \
            else []
        # Get the first SecurityContextFilter from the chain
        security_context_filter = six.next(
            six.moves.filter(
                lambda f: isinstance(f, SecurityContextFilter),
                provider_chain),
            None)
        self._legacy_security_context_filter = None
        if not security_context_filter:
            # Add the Legacy filter if no security context filter is present
            self._legacy_security_context_filter = LegacySecurityContextFilter()
            provider_chain.append(self._legacy_security_context_filter)
        provider_chain.append(api_provider)
        # Chain the providers
        num_providers = len(provider_chain)
        for i, provider in enumerate(provider_chain):
            if i < num_providers - 1:
                provider.next_provider = provider_chain[i + 1]
        self._api_provider = provider_chain[0]
        self._application_context = None

    @abc.abstractmethod
    def connect(self):
        """ rpc provider connect """

    @abc.abstractmethod
    def disconnect(self):
        """ rpc provider disconnect """

    def set_application_context(self, ctx):
        """
        Set the application context

        All the subsequent calls made using this
        connector will use this as the application
        context in the ExecutionContext

        :type  ctx: :class:`vmware.vapi.core.ApplicationContext`
        :param ctx: New application context
        """
        self._application_context = ctx

    def set_security_context(self, ctx):
        """
        Set the security context

        All the subsequent calls made using this
        connector will use this as the security
        context in the ExecutionContext

        :type  ctx: :class:`vmware.vapi.core.SecurityContext`
        :param ctx: New security context
        """
        if not self._legacy_security_context_filter:
            return
            # raise?
        self._legacy_security_context_filter.set_security_context(ctx)

    def new_context(self, runtime_data=None):
        """
        create new execution context object

        :type  runtime_data: :class:`vmware.vapi.core.RuntimeData`    # pylint: disable=line-too-long
        :param runtime_data: Http runtime data
        :rtype:  :class:`vmware.vapi.core.ExecutionContext`
        :return: execution context
        """
        app_ctx = self._application_context
        # Create a default application context only if
        # the user has not provided anything
        if app_ctx is None:
            app_ctx = create_default_application_context()

        if runtime_data is None:
            runtime_data = RuntimeData()

        return ExecutionContext(application_context=app_ctx,
                                runtime_data=runtime_data)

    def get_api_provider(self):
        """
        get api provider

        :rtype:  :class:`vmware.vapi.core.ApiProvider`
        :return: api provider
        """
        return self._api_provider
