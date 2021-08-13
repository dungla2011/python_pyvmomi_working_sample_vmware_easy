"""
StubConfiguration factory
"""
__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015, 2019 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import itertools

from vmware.vapi.bindings.error import VapiError
from vmware.vapi.bindings.stub import StubConfiguration
from com.vmware.vapi.std import errors_client


class StubConfigurationFactory(object):
    """
    Factory class for creating stub configuration objects
    """
    @staticmethod
    def new_configuration(connector, *errorTypes):
        """
        Return a stub configuration using the specified connection, with no
        registered errors.

        :type  connector:
            :class:`vmware.vapi.protocol.client.connector.Connector`
        :param connector: Connection to be used to talk to the remote
                          ApiProvider
        :type  error_types: :class:`list` of
            :class:`vmware.vapi.bindings.type.ErrorType`
        :param error_types: error types to be registered in the configuration
        """
        config = StubConfiguration(connector, *errorTypes)
        return config

    @staticmethod
    def new_runtime_configuration(connector, *errorTypes, **kwargs):
        """
        Return a stub configuration using the specified connection, with the
        errors reported by the vAPI runtime registered.

        :type  connector:
            :class:`vmware.vapi.protocol.client.connector.Connector`
        :param connector: Connection to be used to talk to the remote
                          ApiProvider
        :type  error_types: :class:`list` of
            :class:`vmware.vapi.bindings.type.ErrorType`
        :type kwargs: :class: `vmware.vapi.bindings.http_helper.ResponseExtractor`    # pylint: disable=line-too-long
        :param kwargs: Extract rest http response status
        :param error_types: additional error types to be registered in the
                            configuration
        """
        extractor = kwargs.get('response_extractor', None)
        return StubConfiguration(
            connector,
            errors_client.InternalServerError.get_binding_type(),
            errors_client.InvalidArgument.get_binding_type(),
            errors_client.OperationNotFound.get_binding_type(),
            *errorTypes,
            response_extractor=extractor)

    @staticmethod
    def new_std_configuration(connector, *errorTypes):
        """
        Return a stub configuration using the specified connection, with all the
        standard errors registered.

        :type  connector:
            :class:`vmware.vapi.protocol.client.connector.Connector`
        :param connector: Connection to be used to talk to the remote
                          ApiProvider
        :type  error_types: :class:`list` of
            :class:`vmware.vapi.bindings.type.ErrorType`
        :param error_types: additional error types to be registered in the
                            configuration
        """
        std_errors = (getattr(errors_client, name).get_binding_type()
                      for name in dir(errors_client)
                      if getattr(errors_client, name) is not VapiError
                      and isinstance(getattr(errors_client, name), type)
                      and issubclass(getattr(errors_client, name),
                                     VapiError))
        return StubConfigurationFactory.new_configuration(
            connector,
            *itertools.chain(std_errors, errorTypes))
