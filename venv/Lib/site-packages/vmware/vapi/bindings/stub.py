"""
Stub helper classes
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015, 2017, 2019 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import six

from vmware.vapi.bindings.converter import RestConverter, TypeConverter
from vmware.vapi.bindings.error import UnresolvedError
from vmware.vapi.bindings.common import (
    raise_core_exception, NameToTypeResolver)
from vmware.vapi.bindings.http_helper import ResponseExtractor
from vmware.vapi.core import (
    MethodIdentifier, InterfaceDefinition, MethodDefinition)
from vmware.vapi.core import InterfaceIdentifier, ApiInterface, RuntimeData
from vmware.vapi.exception import CoreException
from vmware.vapi.l10n.runtime import message_factory
from vmware.vapi.lib.constants import OPID
from vmware.vapi.lib.converter import Converter
from vmware.vapi.lib.load import dynamic_import
from vmware.vapi.lib.log import get_vapi_logger
from vmware.vapi.protocol.client.msg.rest_connector import RestClientProvider
from vmware.vapi.provider.filter import ApiProviderFilter

logger = get_vapi_logger(__name__)


class StubConfiguration(object):
    """
    Configuration data for vAPI stub classes

    :type connector: :class:`vmware.vapi.protocol.client.connector.Connector`
    :ivar connector: Connection to be used to talk to the remote ApiProvider
    """
    def __init__(self, connector, *error_types, **kwargs):
        """
        Initialize the stub configuration

        :type  connector: :class:
                          `vmware.vapi.protocol.client.connector.Connector`
        :param connector: Connection to be used to talk to the remote
                          ApiProvider
        :type  error_types: :class:`list` of :class:
                            `vmware.vapi.bindings.type.ErrorType`
        :param error_types: error types to be registered in this configuration
        :type kwargs: :class: `ResponseExtractor`
        :param kwargs: Extract rest http response status
        """
        if connector is None:
            raise TypeError('Input parameter connector is None')
        self._connector = connector
        self._resolver = NameToTypeResolver(
            dict([(e.definition.name, e) for e in error_types]))   # pylint: disable=R1717

        # In order to make it working for both 2.7 and 3.x,
        # based on PEP 3102, use **kwargs with key of response_extractor
        create_response_extractor = kwargs.get('response_extractor', False)
        if create_response_extractor:
            self._response_extractor = ResponseExtractor()
        else:
            self._response_extractor = None

    @property
    def connector(self):
        """
        :rtype: :class:`vmware.vapi.protocol.client.connector.Connector`
        :return: Connection to be used to talk to the remote ApiProvider
        """
        return self._connector

    @property
    def resolver(self):
        """
        Type resolver that can resolve canonical names to its binding types

        :rtype: :class:`vmware.vapi.bindings.common.NameToTypeResolver`
        :return: Type resolver
        """
        return self._resolver

    @property
    def response_extractor(self):
        """
        Response extractor that can retrive the raw http response status and body    # pylint: disable=line-too-long

        :rtype: :class:`vmware.vapi.bindings.http_helper.ResponseExtractor`
        :return: Response extractor
        """
        return self._response_extractor


# We don't need all the methods in ApiMethod in the stub.
# So disabling method not implemented pylint error
class ApiInterfaceStub(ApiInterface):  # pylint: disable=W0223
    """
    Stub class for Api Interface
    """
    def __init__(self, iface_name, config, operations, rest_metadata=None,
                 is_vapi_rest=None):
        """
        Initialize the ApiMethod skeleton object

        :type  iface_name: :class:`str`
        :param iface_name: Interface name
        :type  config: :class:`StubConfiguration`
        :param config: Configuration data for vAPI stubs
        :type  operations: :class:`dict`
        :param operations: Dictionary of operation name to operation information
        :type  rest_metadata: :class:`dict` of :class:`str` and
            :class::`vmware.vapi.lib.rest.OperationRestMetadata`
        :param rest_metadata: Dictionary of operation name to operation REST
            metadata
        :type  is_vapi_rest: :class:`bool`
        :param is_vapi_rest: Json message format. True for Vapi Rest and False
            for Swagger Rest
        """
        self._iface_id = InterfaceIdentifier(iface_name)
        self._config = config
        self._operations = operations
        self._api_provider = config.connector.get_api_provider()
        self._rest_metadata = rest_metadata or {}
        self._is_vapi_rest = is_vapi_rest
        if isinstance(self._api_provider, ApiProviderFilter):
            # Get the API Provider (last provider in the chain)
            last_api_provider = self._api_provider.get_api_provider()
        else:
            last_api_provider = self._api_provider
        self._response_extractor = None
        # Determine whether REST format needs to be used
        self._use_rest = True if isinstance(                 # pylint: disable=R1719
            last_api_provider, RestClientProvider) else False
        if self._use_rest:
            # Add the service metadata to the REST provider
            last_api_provider.set_rest_format(self._is_vapi_rest)
            for method_name, operation_rest_metadata in six.viewitems(
                    self._rest_metadata):
                last_api_provider.add_rest_metadata(
                    self._iface_id.get_name(), method_name,
                    operation_rest_metadata)
            # Set the REST converter mode
            if is_vapi_rest:
                self._rest_converter_mode = RestConverter.VAPI_REST
            else:
                self._rest_converter_mode = RestConverter.SWAGGER_REST
            self._response_extractor = self._config._response_extractor   # pylint: disable=W0212
        else:
            self._rest_converter_mode = None
        ApiInterface.__init__(self)

    def get_identifier(self):
        """
        Returns interface identifier

        :rtype: :class:`InterfaceIdentifier`
        :return: Interface identifier
        """
        return self._iface_id

    def get_definition(self):
        """
        Returns interface definition

        :rtype: :class:`InterfaceDefinition`
        :return: Interface definition
        """
        operations = [MethodIdentifier(self._iface_id, operation_name)
                      for operation_name in six.iterkeys(self._operations)]
        return InterfaceDefinition(self._iface_id, operations)

    def get_method_definition(self, method_id):                # pylint: disable=R1710
        op_info = self._operations.get(method_id.get_name())
        if op_info is None:
            return

        errors_defs = [
            e.definition for e in six.itervalues(op_info.get('errors'))]
        return MethodDefinition(method_id,
                                op_info.get('input_type').definition,
                                op_info.get('output_type').definition,
                                errors_defs)

    def invoke(self, ctx, method_id, input_value):
        """
        Invokes the specified method using the execution context and
        the input provided

        :type  ctx: :class:`vmware.vapi.core.ExecutionContext`
        :param ctx: Execution context for this method
        :type  method_id: :class:`vmware.vapi.core.MethodIdentifier`
        :param method_id: Method identifier
        :type  input_value: :class:`vmware.vapi.data.value.StructValue`
        :param input_value: Method input parameters

        :rtype: :class:`vmware.vapi.core.MethodResult`
        :return: Result of the method invocation
        """
        return self._api_provider.invoke(self._iface_id.get_name(),
                                         method_id.get_name(),
                                         input_value,
                                         ctx)

    def native_invoke(self, ctx, method_name, kwargs):
        """
        Invokes the method corresponding to the given method name
        with the kwargs.

        In this method, python native values are converted to vAPI
        runtime values, operation is invoked and the result are converted
        back to python native values

        :type  ctx: :class:`vmware.vapi.core.ExecutionContext`
        :param ctx: Execution context for this method
        :type  method_name: :class:`str`
        :param method_name: Method name
        :type  kwargs: :class:`dict`
        :param kwargs: arguments to be passed to the method
        :rtype: :class:`object`
        :return: Method result
        """
        op_info = self._operations.get(method_name)
        if op_info is None:
            raise Exception('Could not find %s method in %s interface' %
                            (method_name, str(self._iface_id)))

        # Convert input
        input_type = op_info['input_type']
        data_val = TypeConverter.convert_to_vapi(kwargs, input_type,
                                                 self._rest_converter_mode)

        # Validate input
        validators = op_info['input_value_validator_list']
        for validator in validators:
            msg_list = validator.validate(data_val, input_type)
            raise_core_exception(msg_list)

        if OPID in ctx.application_context:
            logger.debug(
                'opId: %s invoke: interface_id: %s, operation_name: %s',
                ctx.application_context[OPID], self._iface_id.get_name(),
                method_name)
        else:
            logger.debug('invoke: interface_id: %s, operation_name: %s',
                         self._iface_id, method_name)

        # Invoke
        method_id = MethodIdentifier(self._iface_id, method_name)
        if self._use_rest:
            operation_rest_metadata = None
            if self._rest_metadata:
                operation_rest_metadata = self._rest_metadata.get(method_name)
            if operation_rest_metadata is None:
                msg = message_factory.get_message(
                    'vapi.bindings.stub.rest_metadata.unavailable')
                logger.debug(msg)
                raise CoreException(msg)
        else:
            if self._is_vapi_rest is not None and not self._is_vapi_rest:
                # If the rest format is not vapi, then the server
                # (OpenAPI based) will not be supporting json-rpc.
                msg = message_factory.get_message(
                    'vapi.bindings.stub.jsonrpc.unsupported')
                logger.debug(msg)
                raise CoreException(msg)
        method_result = self.invoke(ctx, method_id, data_val)

        # Validate output
        if method_result.success():
            validators = op_info['output_validator_list']
            output_type = op_info['output_type']

            for validator in validators:
                msg_list = validator.validate(method_result.output, output_type)
                raise_core_exception(msg_list)

            # Convert output
            return TypeConverter.convert_to_python(method_result.output,
                                                   output_type,
                                                   self._config.resolver,
                                                   self._rest_converter_mode)
        else:
            # Convert error
            errors = op_info['errors']
            error_type = errors.get(method_result.error.name)
            if error_type is None:
                error_type = self._config.resolver.resolve(
                    method_result.error.name)
            if error_type is None:
                logger.warning('Unable to convert unexpected vAPI error %s '   # pylint: disable=W1201
                               + 'to native Python exception',
                               method_result.error.name)
                vapi_error = UnresolvedError(method_result.error)
                raise vapi_error
            raise TypeConverter.convert_to_python(method_result.error,  # pylint: disable=E0702
                                                  error_type,
                                                  self._config.resolver,
                                                  self._rest_converter_mode)


class VapiInterface(object):
    """
    vAPI Interface class is used by the python client side bindings. This
    encapsulates the ApiInterfaceStub instance
    """
    def __init__(self, config, api_interface):
        """
        Initialize VapiInterface object

        :type  config: :class:`StubConfiguration`
        :param config: Configuration data for vAPI stubs
        :type  api_interface: :class:`ApiInterfaceStub`
        :param api_interface: Instance of ApiInterfaceStub class that can
                              execute the ApiMethods
        """
        if config is None:
            raise TypeError('Input parameter config is None')
        if isinstance(config, StubConfiguration):
            self._config = config
        else:
            raise TypeError('Input parameter config is not a StubConfiguration')
        self._api_interface = api_interface(self._config)

    def _invoke(self, _method_name, kwargs):
        """
        Invokes the ApiMethod corresponding to the given method name
        with the kwargs

        :type  _method_name: :class:`str`
        :param _method_name: Method name
        :type  kwargs: :class:`dict` of :class:`str` and :class:`object`
                       or :class:`None`
        :param kwargs: arguments to be passed to the method
        :return: Method result
        """
        kwargs = kwargs or {}
        # Argument name is _method_name to make sure it doesn't collide
        # with actual parameter names of the method
        if (self._config._response_extractor):           # pylint: disable=W0212
            runtime_data = RuntimeData(
                {'response_extractor': self._config._response_extractor})    # pylint: disable=W0212
            ctx = self._config.connector.new_context(runtime_data)
        else:
            ctx = self._config.connector.new_context()
        return self._api_interface.native_invoke(ctx, _method_name, kwargs)


class StubFactory(object):
    """
    Factory for client-side vAPI stubs
    """
    def __init__(self, config):
        """
        Initialize the stub factory

        :type  config: :class:`StubConfiguration`
        :param config: Configuration data for vAPI stubs
        """
        if config is None:
            raise TypeError('Input parameter config is None')
        if not isinstance(config, StubConfiguration):
            raise TypeError('Input parameter config is not a StubConfiguration')
        self._config = config

    def create_stub(self, service_name):
        """
        Create a stub corresponding to the specified service name

        :type  service_name: :class:`str`
        :param service_name: Name of the service

        :rtype: :class:`VapiInterface`
        :return: The stub correspoding to the specified service name
        """
        path_split = service_name.split('.')
        module_name = '%s_client' % '.'.join(path_split[:-1])
        class_name = Converter.underscore_to_capwords(path_split[-1])
        module = __import__(module_name, globals(), locals(), class_name)
        cls = getattr(module, class_name)
        return cls(self._config)


class StubFactoryBase(object):
    """
    Class that represents a VMODL2 package and holds the stubs for services
    which are part of that package as well as stub factories of sub-packages

    :type _attrs: :class:`dict` of :class:`str` and
        (:class:`vmware.vapi.bindings.stub.VapiInterface` or :class:`str`)
    :cvar _attrs: Dictionary of service name and service stub or sub module name
        and string reprensenting the fully qualified class path
    """
    _attrs = {}

    def __init__(self, stub_config):
        """
        Initialize StubFactoryBase

        :type  stub_config: :class:`vmware.vapi.bindings.stub.StubConfiguration`
        :param stub_config: Stub config instance
        """
        self._stub_config = stub_config
        for k, val in six.viewitems(self._attrs):
            if isinstance(val, six.string_types):
                # If the value in the _attr dict is a string, then import the
                # type and set it as the value in the same dict
                val = dynamic_import(val)
                self._attrs[k] = val
            # Set every key, value in _attrs dict as an instance variable
            setattr(self, k, val)

    def __getattribute__(self, name):
        result = object.__getattribute__(self, name)
        if name in ['_attrs', '_stub_config']:
            # Ignore them for further processing and just return
            return result
        if (name in self._attrs
                and not isinstance(result, (StubFactoryBase, VapiInterface))):
            # If the result is not a stub or stub factory instance, create an
            # instance using the saved stub config and set them on this object
            # itself so that it can be reused
            result = result(self._stub_config)
            setattr(self, name, result)
        return result


class ApiClient(object):
    """
    Base Class that represents an api client that client binding users can use
    to access all the service stubs
    """
    def __init__(self, stub_factory):
        """
        Initialize ApiClient

        :type  stub_factory: :class:`vmware.vapi.bindings.stub.StubFactoryBase`
        :param stub_factory: Instance for the top level stub factory for the API
            component or product
        """
        self._stub_factory = stub_factory

    def __getattr__(self, name):
        return getattr(self._stub_factory, name)

    def __dir__(self):
        return dir(self._stub_factory)
