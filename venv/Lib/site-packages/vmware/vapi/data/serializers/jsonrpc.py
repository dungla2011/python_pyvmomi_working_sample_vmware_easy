# -*- coding: utf-8 -*-

"""
Json rpc de/serializer
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015, 2017, 2019 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long


import base64
import decimal
import json
import six

from vmware.vapi.core import (
    MethodResult, ExecutionContext, ApplicationContext, SecurityContext)
from vmware.vapi.data.type import Type
from vmware.vapi.data.value import (
    data_value_factory, StructValue, ErrorValue, ListValue,
    OptionalValue, VoidValue, StringValue, BooleanValue, IntegerValue,
    DoubleValue, BlobValue, SecretValue)
from vmware.vapi.lib.jsonlib import canonicalize_double
from vmware.vapi.lib.log import get_vapi_logger

logger = get_vapi_logger(__name__)

# Vapi json rpc version
VAPI_JSONRPC_VERSION = '2.0'

# Vapi json rpc method names
VAPI_INVOKE = 'invoke'

vapi_to_json_map = {
    Type.BLOB: 'BINARY',
    Type.SECRET: 'SECRET',
    Type.ERROR: 'ERROR',
    Type.STRUCTURE: 'STRUCTURE',
    Type.OPTIONAL: 'OPTIONAL',
}

json_to_vapi_map = dict((v, k) for k, v in six.iteritems(vapi_to_json_map))


class VAPIJsonEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that converts vAPI runtime types directly
    into JSON string representation.
    """
    # Even though __init__ is called below, pylint throws a warning
    # that base class __init__ is not called (W0231)
    def __init__(self, *args, **kwargs):  # pylint: disable=W0231
        self._dispatch_map = {
            MethodResult: self.visit_method_result,
            ExecutionContext: self.visit_execution_context,
            dict: self.visit_dict,
            list: self.visit_list,
            decimal.Decimal: canonicalize_double,
            StructValue: self.visit_struct_value,
            ErrorValue: self.visit_struct_value,
            ListValue: self.visit_list,
            OptionalValue: self.visit_optional_value,
            DoubleValue: self.visit_double_value,
            IntegerValue: self.visit_primitive_value,
            BooleanValue: self.visit_primitive_value,
            StringValue: self.visit_primitive_value,
            VoidValue: self.visit_primitive_value,
            BlobValue: self.visit_blob_value_with_type_name,
            SecretValue: self.visit_primitive_value_with_type_name,
        }
        json.JSONEncoder.__init__(self, *args, **kwargs)

    #
    # Even though the recommended way to subclass JSONEncoder is by overriding
    # "default", encode is being used as it will preserve the computed JSON
    # string literal for decimals. If we use default, the value returned by
    # canonicalize_double will be wrapped inside double quotes in the final
    # JSON message.
    #
    def encode(self, value):
        """
        Encode a given vAPI runtime object

        :type  value: :class:`object`
        :param value: vAPI runtime object
        :rtype: :class:`str`
        :return: JSON string
        """
        return self._dispatch_map.get(type(value), self.visit_default)(value)

    def visit_struct_value(self, value):
        """
        Visit a StructValue object

        :type  value: :class:`vmware.vapi.data.value.StructValue`
        :param value: Struct value object
        :rtype: :class:`str`
        :return: JSON string
        """
        type_name = vapi_to_json_map.get(value.type)
        items = ['"%s":%s' % (k, self.encode(v))
                 for k, v in value.get_fields()]
        return '{"%s":{"%s":{%s}}}' % (
            type_name,
            value.name,
            ','.join(items))

    def visit_list(self, value):
        """
        Visit a ListValue object

        :type  value: :class:`vmware.vapi.data.value.ListValue`
        :param value: List value object
        :rtype: :class:`str`
        :return: JSON string
        """
        string = ','.join([self.encode(item)
                          for item in value])
        return '[%s]' % string

    def visit_optional_value(self, value):
        """
        Visit a OptionalValue object

        :type  value: :class:`vmware.vapi.data.value.OptionalValue`
        :param value: Optional value object
        :rtype: :class:`str`
        :return: JSON string
        """
        type_name = vapi_to_json_map.get(value.type)
        if value.is_set():
            return '{"%s":%s}' % (type_name, self.encode(value.value))
        else:
            return '{"%s":null}' % type_name

    @staticmethod
    def visit_double_value(value):
        """
        Visit a DoubleValue object

        :type  value: :class:`vmware.vapi.data.value.DoubleValue`
        :param value: Double value object
        :rtype: :class:`str`
        :return: JSON string
        """
        return canonicalize_double(value.value)

    def visit_primitive_value(self, value):
        """
        Visit one of StringValue, IntegerValue, BooleanValue or VoidValue

        :type  value: :class:`vmware.vapi.data.value.StringValue` (or)
            :class:`vmware.vapi.data.value.IntegerValue` (or)
            :class:`vmware.vapi.data.value.BooleanValue` (or)
            :class:`vmware.vapi.data.value.VoidValue` (or)
        :param value: StringValue, IntegerValue, BooleanValue or VoidValue
            object
        :rtype: :class:`str`
        :return: JSON string
        """
        return json.JSONEncoder.encode(self, value.value)

    def visit_primitive_value_with_type_name(self, value):
        """
        Visit SecretValue

        :type  value: :class:`vmware.vapi.data.value.SecretValue`
        :param value: SecretValue object
        :rtype: :class:`str`
        :return: JSON string
        """
        type_name = vapi_to_json_map.get(value.type)
        return '{"%s":%s}' % (type_name, self.encode(value.value))

    def visit_blob_value_with_type_name(self, value):
        """
        Visit BlobValue

        :type  value: :class:`vmware.vapi.data.value.BlobValue`
        :param value: BlobValue object
        :rtype: :class:`str`
        :return: JSON string
        """
        type_name = vapi_to_json_map.get(value.type)
        base64_encoded_value = base64.b64encode(value.value)
        # Convert to unicode since Python3 json library doesn't allow bytes.
        # Python2 json library allows both. But we will always deal in unicode
        # since we get unicode while converting from JSON to Python objects
        unicode_value = base64_encoded_value.decode()
        return '{"%s":%s}' % (type_name, self.encode(unicode_value))

    def visit_method_result(self, value):
        """
        Visit a MethodResult object

        :type  value: :class:`vmware.vapi.core.MethodResult`
        :param value: MethodResult object
        :rtype: :class:`str`
        :return: JSON string
        """
        if value.error is not None:
            return '{"%s":%s}' % ('error', self.encode(value.error))
        elif value.output is not None:
            return '{"%s":%s}' % ('output', self.encode(value.output))

        return None

    def visit_execution_context(self, value):
        """
        Visit an ExecutionContext object

        :type  value: :class:`vmware.vapi.core.ExecutionContext`
        :param value: ExecutionContext object
        :rtype: :class:`str`
        :return: JSON string
        """
        if value.security_context:
            return '{"%s":%s,"%s":%s}' % (
                'appCtx',
                self.encode(value.application_context),
                'securityCtx',
                self.encode(value.security_context))
        else:
            return '{"%s":%s}' % ('appCtx',
                                  self.encode(value.application_context))

    def visit_dict(self, value):
        """
        Visit a dictionary. Application context and Security Context
        in vAPI is a free form object, so it can contain a dictionary.

        :type  value: :class:`dict`
        :param value: Dictionary value
        :rtype: :class:`str`
        :return: JSON string
        """
        items = ['%s:%s' % (self.encode(k), self.encode(v))
                 for k, v in six.iteritems(value)]
        return '{%s}' % ','.join(items)

    def visit_default(self, value):
        """
        This is the default visit method if the type of the input value
        does not match any type in the keys present in dispatch map.

        :type  value: :class:`object`
        :param value: Python object
        :rtype: :class:`str`
        :return: JSON string
        """
        return json.JSONEncoder.encode(self, value)


class JsonRpcDictToVapi(object):
    """ Json rpc dict to vapi type """

    def __init__(self):
        """ Json rpc dict to vapi type init """

    @staticmethod
    def data_value(value):
        """
        get data value from new jsonrpc dict

        # TODO: Structure names and its fields are converted from
        # u'' format to str format. This will break if we allow non
        # ASCII characters in the IDL

        :type  value: :class:`dict`
        :param value: json data value
        :rtype:  subclass of :class:`vmware.vapi.data.value.DataValue`
        :return: subclass of data value
        """
        result = None
        if value is None:
            result = data_value_factory(Type.VOID)
        elif isinstance(value, dict):
            # Optional, Secret, Blob, Error, Structure
            # types are inside object
            if len(value) > 1:
                raise vapi_jsonrpc_error_invalid_params()
            (type_name, json_value) = value.popitem()
            typ = json_to_vapi_map[type_name]
            if typ == Type.SECRET:
                result = data_value_factory(typ, json_value)
            elif typ == Type.BLOB:
                # For Blob types, the string json value will be base64 encoded
                # and UTF-8 decoded
                unicode_json_value = json_value
                base64_encoded_value = unicode_json_value.encode()
                try:
                    bytes_value = base64.b64decode(base64_encoded_value)
                    result = data_value_factory(typ, bytes_value)
                except Exception as err:
                    if six.PY2 and isinstance(err, TypeError):
                        raise vapi_jsonrpc_error_internal_error()
                    elif six.PY3:
                        import binascii
                        if isinstance(err, binascii.Error):
                            raise vapi_jsonrpc_error_internal_error()
                    raise
            elif typ in [Type.ERROR, Type.STRUCTURE]:
                if len(json_value) > 1:
                    raise vapi_jsonrpc_error_invalid_params()
                struct_name, fields = json_value.popitem()
                result = data_value_factory(typ, str(struct_name))
                for field_name, field_value in six.iteritems(fields):
                    field_data_value = JsonRpcDictToVapi.data_value(
                        field_value)
                    result.set_field(str(field_name), field_data_value)
            elif typ == Type.OPTIONAL:
                result = data_value_factory(typ)
                if json_value is not None:
                    result.value = JsonRpcDictToVapi.data_value(json_value)
        elif isinstance(value, list):
            # ListValue is json list
            list_data_values = [JsonRpcDictToVapi.data_value(val)
                                for val in value]
            result = data_value_factory(Type.LIST, list_data_values)
        elif isinstance(value, bool):
            result = data_value_factory(Type.BOOLEAN, value)
        elif isinstance(value, six.string_types):
            result = data_value_factory(Type.STRING, value)
        elif isinstance(value, six.integer_types):
            result = data_value_factory(Type.INTEGER, value)
        else:
            # For Double
            result = data_value_factory(Type.DOUBLE, value)
        return result

    @staticmethod
    def error_value(value):
        """
        get error value from jsonrpc dict

        :type  msg: :class:`dict`
        :param msg: json error value
        :rtype:  :class:`vmware.vapi.data.value.ErrorValue`
        :return: error value
        """
        return JsonRpcDictToVapi.data_value(value)

    @staticmethod
    def method_result(result):
        """
        get method result from jsonrpc dict

        :type  result: :class:`dict`
        :param result: json method result
        :rtype:  :class:`vmware.vapi.core.MethodResult`
        :return: method result
        """
        output = None
        if 'output' in result:
            output = JsonRpcDictToVapi.data_value(result['output'])
        error = None
        if 'error' in result:
            error = JsonRpcDictToVapi.error_value(result['error'])
        return MethodResult(output=output, error=error)

    @staticmethod
    def security_ctx(ctx):
        """
        get security context from jsonrpc dict

        :type  ctx: :class:`dict`
        :param ctx: json security context
        :rtype:  :class:`vmware.vapi.core.SecurityContext`
        :return: json user session
        """
        if ctx is not None:
            return SecurityContext(ctx)

        return None

    @staticmethod
    def app_ctx(ctx):
        """
        get application context from jsonrpc dict

        :type  ctx: :class:`dict`
        :param ctx: json application context
        :rtype:  :class:`str`
        :return: operation identifier
        """
        return ApplicationContext(ctx)

    @staticmethod
    def execution_context(ctx):
        """
        get execution context from jsonrpc dict

        :type  ctx: :class:`dict`
        :param ctx: json execution context
        :rtype:  :class:`vmware.vapi.core.ExecutionContext`
        :return: execution context
        """
        app_ctx = JsonRpcDictToVapi.app_ctx(ctx.get('appCtx'))
        security_ctx = JsonRpcDictToVapi.security_ctx(ctx.get('securityCtx'))
        execution_context = ExecutionContext(app_ctx, security_ctx)
        return execution_context


class JsonRpcError(Exception):
    """ json rpc error base class """

    def __init__(self, error):
        """
        json rpc error base class constructor

        :type  error: :class:`dict`
        :param error: json rpc error
        """
        Exception.__init__(self)
        self.error = error


class JsonRpcRequest(object):
    """ Json rpc request base class """

    def __init__(self, version, method, params=None, notification=True,
                 request_id=None):
        """
        Json rpc request base class constructor

        :type  version: :class:`str`
        :kwarg version: json rpc request version
        :type  method: :class:`str`
        :kwarg method: json rpc method
        :type  params: :class:`dict` or :class:`list` or None
        :kwarg params: json rpc method params
        :type  notification: :class:`bool`
        :kwarg notification: True for notification
        :type  request_id: :class:`long` or :class:`int` or :class:`str` or None
        :kwarg request_id: json rpc request id. Do not set for notification
        """
        self.version = version
        if not isinstance(method, six.string_types):
            raise vapi_jsonrpc_error_invalid_request()
        self.method = method
        self.params = params
        self.notification = notification
        self.id = request_id

    def serialize(self):
        """
        Serialize a json rpc request

        :rtype: :class:`str`
        :return: json rpc request str
        """
        raise NotImplementedError

    def validate_response(self, response):
        """
        Validate a json rpc response.
        Check for version / id mismatch with request

        :type  response: :class:`JsonRpcResponse`
        :param response: json rpc response object to validate
        """
        raise NotImplementedError


class JsonRpcResponse(object):
    """ Json rpc response base class """

    def __init__(self, version, response_id, result, error=None):
        """
        Json rpc response base class constructor

        :type  version: :class:`str`
        :kwarg version: json rpc response version
        :type  response_id: :class:`long` or :class:`int` or :class:`str` or
            None
        :kwarg response_id: json rpc response id
        :type  result: :class:`dict`
        :kwarg result: json rpc response dict
        :type  error: :class:`JsonRpcError`
        :kwarg error: json rpc error
        """

        self.version = version
        self.id = response_id
        # result or error, but not both
        if result is not None and error is not None:
            logger.error('JSON RPC response has both result and error')
            raise vapi_jsonrpc_error_invalid_params()
        elif result is None and error is None:
            logger.error('JSON RPC response has neither result nor error')
            raise vapi_jsonrpc_error_invalid_params()
        else:
            self.result, self.error = result, error

    def serialize(self):
        """
        Serialize a json rpc response

        :rtype: :class:`str`
        :return: json rpc response str
        """
        raise NotImplementedError


class JsonRpc20Error(JsonRpcError):
    """ json rpc 2.0 error """

    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    PARSE_ERROR = -32700
    INVALID_OPERATION = -31001

    # TRANSPORT_ERROR is defined in xmlrpc error code
    #  http://xmlrpc-epi.sourceforge.net/specs/rfc.fault_codes.php
    # but not JSON RPC 2.0
    # Need this for server connection error
    TRANSPORT_ERROR = -32300

    # All errors codes above have to be in error range below.
    SERVER_ERROR_RANGE_MIN = -32768
    SERVER_ERROR_RANGE_MAX = -31000

    DEFAULT_MESSAGES = {
        INVALID_REQUEST: 'Invalid Request.',
        METHOD_NOT_FOUND: 'Method not found.',
        INVALID_PARAMS: 'Invalid params.',
        INTERNAL_ERROR: 'Internal error.',
        PARSE_ERROR: 'Parse error.',
        TRANSPORT_ERROR: 'Transport error.',
        INVALID_OPERATION: 'Mismatching operation identifier in HTTP header'
                           'and payload',
    }

    def __init__(self, code, message=None, data=None):
        """
        Json rpc 2.0 error

        :type  code: :class:`int`
        :kwarg code: error type that occurred
        :type  message: :class:`str`
        :kwarg message: a short description of the error
        :type  data: Primitive type / :class:`dict` / None
        :kwarg data: more info about the error
        """
        try:
            code = int(code)
        except ValueError:
            logger.error('JSON RPC error code type: Expecting "int". Got "%s"',
                         str(type(code)))
            raise
        self.code = code
        if message is None and (code >= self.SERVER_ERROR_RANGE_MIN
                                or code <= self.SERVER_ERROR_RANGE_MAX):
            message = self.DEFAULT_MESSAGES.get(code, 'Server error.')
        self.json_message = message
        error = {'code': code, 'message': message}
        if data:
            error['data'] = str(data)
        self.data = data
        JsonRpcError.__init__(self, error)

    def __str__(self):
        return '%d: %s: %s' % (
            self.code, str(self.json_message), str(self.data))


def vapi_jsonrpc_error_parse_error(data=None):
    """
    vapi json rpc parse error

    :type  data: :class:`dict`
    :param data: json rpc error object
    :rtype: :class:`JsonRpcError`
    :return: json rpc error object
    """
    return JsonRpc20Error(code=JsonRpc20Error.PARSE_ERROR, data=data)


def vapi_jsonrpc_error_invalid_request(data=None):
    """
    vapi json rpc invalid request error

    :type  data: :class:`dict`
    :param data: json rpc error object
    :rtype: :class:`JsonRpcError`
    :return: json rpc error object
    """
    return JsonRpc20Error(code=JsonRpc20Error.INVALID_REQUEST, data=data)


def vapi_jsonrpc_error_method_not_found(data=None):
    """
    vapi json rpc method not found error

    :type  data: :class:`dict`
    :param data: json rpc error object
    :rtype: :class:`JsonRpcError`
    :return: json rpc error object
    """
    return JsonRpc20Error(code=JsonRpc20Error.METHOD_NOT_FOUND, data=data)


def vapi_jsonrpc_error_invalid_params(data=None):
    """
    vapi json rpc invalid params error

    :type  data: :class:`dict`
    :param data: json rpc error object
    :rtype: :class:`JsonRpcError`
    :return: json rpc error object
    """
    return JsonRpc20Error(code=JsonRpc20Error.INVALID_PARAMS, data=data)


def vapi_jsonrpc_error_internal_error(data=None):
    """
    vapi json rpc internal error

    :type  data: :class:`dict`
    :param data: json rpc error object
    :rtype: :class:`JsonRpcError`
    :return: json rpc error object
    """
    return JsonRpc20Error(code=JsonRpc20Error.INTERNAL_ERROR, data=data)


def vapi_jsonrpc_error_transport_error(data=None):
    """
    vapi json rpc transport error

    :type  data: :class:`dict`
    :param data: json rpc error object
    :rtype: :class:`JsonRpcError`
    :return: json rpc error object
    """
    return JsonRpc20Error(code=JsonRpc20Error.TRANSPORT_ERROR, data=data)


def vapi_jsonrpc_error_invalid_operation(data=None):
    """
    vapi json rpc invalid context

    :type  data: :class:`dict`
    :param data: json rpc error object
    :rtype: :class:`JsonRpcError`
    :return: json rpc error object
    """
    return JsonRpc20Error(code=JsonRpc20Error.INVALID_OPERATION, data=data)


class JsonRpc20Request(JsonRpcRequest):
    """ Json rpc 2.0 request """

    def __init__(self, **kwargs):
        """
        Json rpc 2.0 request init

        :type  jsonrpc: :class:`str` or None
        :kwarg jsonrpc: json rpc request version
        :type  method: :class:`str`
        :kwarg method: json rpc method
        :type  params: :class:`dict` or :class:`list` or None
        :kwarg params: json rpc method params
        :type  id: :class:`long` or :class:`int` or :class:`str` or None
        :kwarg id: json rpc request id. Do not set for notification
        """
        version = kwargs.get('jsonrpc')
        notification, id_ = True, None
        if 'id' in kwargs:
            notification, id_ = False, kwargs.get('id')
            if (id_ and not (isinstance(id_, six.string_types)
                             or isinstance(id_, six.integer_types))):
                logger.error(
                    'JSON RPC request id must be None/str/int. Get "%s"',
                    str(type(id_)))
                raise vapi_jsonrpc_error_invalid_request()
        method = kwargs.get('method')
        params = kwargs.get('params')
        if not (params is None or isinstance(params, dict)
                or isinstance(params, list)):
            raise vapi_jsonrpc_error_invalid_request()
        JsonRpcRequest.__init__(self, version=version,
                                method=method,
                                params=params,
                                notification=notification,
                                request_id=id_)

    def serialize(self):
        """
        Serialize a json rpc 2.0 request

        :rtype: :class:`str`
        :return: json rpc request str
        """
        result_dict = {'jsonrpc': self.version,
                       'method': self.method,
                       'params': self.params,
                       'id': self.id}
        return json.dumps(result_dict,
                          check_circular=False,
                          separators=(',', ':'),
                          cls=VAPIJsonEncoder)

    def serialize_notification(self):
        """
        Serialize a json rpc 2.0 notification

        :rtype: :class:`str`
        :return: json rpc notification str
        """
        result_dict = {'jsonrpc': self.version,
                       'method': self.method,
                       'params': self.params}
        return json.dumps(result_dict,
                          check_circular=False,
                          separators=(',', ':'),
                          cls=VAPIJsonEncoder)

    def validate_response(self, response):
        """
        Validate a json rpc 2.0 response.
        Check for version / id mismatch with request

        :type  response: :class:`JsonRpcResponse`
        :param response: json rpc response object to validate
        """
        if self.notification:
            logger.error('JSON RPC notification does not have response')
            raise vapi_jsonrpc_error_invalid_params()

        # Check jsonrpc version
        # NYI: backward compatible?
        request_version = self.version
        if response.version != request_version:
            logger.error('JSON RPC incompatible version: "%s". Expecting "%s"',
                         str(response.version), str(request_version))
            raise vapi_jsonrpc_error_invalid_params()

        # Note: response_id MUST be Null for PARSE_ERROR / INVALID_REQUEST
        # NYI: Relax this requirement?
        if (response.error
                and (response.error.code == JsonRpc20Error.PARSE_ERROR
                     or response.error.code == JsonRpc20Error.INVALID_REQUEST)):
            id_ = None
        else:
            id_ = self.id

        # Check request / response id
        if id_ != response.id:
            logger.error('JSON RPC response id mismatch: "%s". Expecting "%s"',
                         str(response.id), str(id_))
            raise vapi_jsonrpc_error_invalid_params()


class JsonRpc20Response(JsonRpcResponse):
    """ Json rpc 2.0 response """

    def __init__(self, **kwargs):
        """
        Json rpc 2.0 response init
        Either result or error must be set, but not both

        :type  jsonrpc: :class:`str` or None
        :kwarg jsonrpc: json rpc response version
        :type  result: :class:`dict`
        :kwarg result: json rpc response dict
        :type  error: :class:`JsonRpcError` or dict
        :kwarg error: json rpc response error
        :type  id: :class:`long` or :class:`int` or :class:`str`
        :kwarg id: json rpc response id
        """
        version = kwargs.get('jsonrpc')
        id_ = kwargs.get('id')
        # result or error
        result = kwargs.get('result')
        error = kwargs.get('error')
        if error is not None:
            if isinstance(error, JsonRpcError):
                pass
            elif isinstance(error, dict):
                code = error.get('code')
                message = error.get('message')
                error = JsonRpc20Error(code=code, message=message, data=error)
            else:
                logger.error(
                    'JSON RPC params type error. Expecting "%s". Got "%s"',
                    'JsonRpcError / dict', str(type(error)))
                raise vapi_jsonrpc_error_invalid_params()
        JsonRpcResponse.__init__(self, version=version, response_id=id_,
                                 result=result, error=error)

    def serialize(self):
        """
        Serialize a json rpc 2.0 response

        :rtype: :class:`str`
        :return: json rpc response str
        """
        result_dict = {'jsonrpc': self.version,
                       'id': self.id}
        if self.result is not None:
            result_dict['result'] = self.result
        else:
            # result is None, error MUST not be None
            result_dict['error'] = self.error.error
            if (self.error.code == JsonRpc20Error.PARSE_ERROR
                    or self.error.code == JsonRpc20Error.INVALID_REQUEST):
                result_dict['id'] = None
        output = json.dumps(result_dict,
                            check_circular=False,
                            separators=(',', ':'),
                            cls=VAPIJsonEncoder)
        output = output.encode('utf-8')
        return output


def jsonrpc_request_factory(**kwargs):
    """
    Json rpc request factory
    For json 2.0: set jsonrpc to '2.0'
    For json 1.1: set version to '1.1'
    For json 1.0: set neither jsonrpc / version
    The parameters accepted depends on json version
    See corresponding json rpc request class for init parameters

    :type  jsonrpc: :class:`str` or None
    :kwarg jsonrpc: json rpc request version (2.0)
    :type  version: :class:`str` or None
    :kwarg version: json rpc request version (1.1)
    :type  method: :class:`str`
    :kwarg method: json rpc method
    :type  params: :class:`dict` or :class:`list` or None
    :kwarg params: json rpc method params
    :type  id: :class:`long` or :class:`int` or :class:`str` or None
    :kwarg id: json rpc request id. Do not set for notification

    :rtype: :class:`JsonRpcRequest`
    :return: json rpc request object
    """
    jsonrpc_version = kwargs.get('jsonrpc')
    if jsonrpc_version and jsonrpc_version == '2.0':
        # json rpc 2.0
        request = JsonRpc20Request(**kwargs)
    else:
        jsonrpc_version = kwargs.get('version')
        if jsonrpc_version and jsonrpc_version == '1.1':
            # NYI: json rpc 1.1
            # request = JsonRpc11Request(kwargs)
            request = None
        else:
            # NYI: json rpc 1.0
            # request = JsonRpc10Request(kwargs)
            request = None
    return request


def jsonrpc_response_factory(**kwargs):
    """
    Json rpc response factory
    For json 2.0: set jsonrpc to '2.0'
    For json 1.1: set version to '1.1'
    For json 1.0: set neither jsonrpc / version
    The parameters accepted depends on json version
    See corresponding json rpc response class for init parameters

    :type  jsonrpc: :class:`str` or None
    :kwarg jsonrpc: json rpc response version (2.0)
    :type  version: :class:`str` or None
    :kwarg version: json rpc response version (1.1)
    :type  method: :class:`str`
    :kwarg method: json rpc method
    :type  params: :class:`dict` or :class:`list` or None
    :kwarg params: json rpc method params
    :type  id: :class:`long` or :class:`int` or :class:`str`
    :kwarg id: json rpc response id

    :rtype: :class:`JsonRpcResponse`
    :return: json rpc response object
    """
    jsonrpc_version = kwargs.get('jsonrpc')
    if jsonrpc_version and jsonrpc_version == '2.0':
        # json rpc 2.0
        response = JsonRpc20Response(**kwargs)
    else:
        jsonrpc_version = kwargs.get('version')
        if jsonrpc_version and jsonrpc_version == '1.1':
            # NYI: json rpc 1.1
            # response = JsonRpc11Response(kwargs)
            response = None
        else:
            # NYI: json rpc 1.0
            # response = JsonRpc10Response(kwargs)
            response = None
    return response


def vapi_jsonrpc_request_factory(**kwargs):
    """
    Json rpc request factory

    :type  method: :class:`str`
    :kwarg method: json rpc method
    :type  params: :class:`dict` or :class:`list` or None
    :kwarg params: json rpc method params
    :type  id: :class:`long` or :class:`int` or :class:`str` or None
    :kwarg id: json rpc request id. Do not set for notification

    :rtype: :class:`JsonRpcRequest`
    :return: json rpc request object
    """
    jsonrpc_version = kwargs.get('jsonrpc', VAPI_JSONRPC_VERSION)
    # vapi json rpc supports version 2.0 only
    assert(jsonrpc_version == VAPI_JSONRPC_VERSION)
    kwargs.setdefault('jsonrpc', jsonrpc_version)
    return JsonRpc20Request(**kwargs)


def vapi_jsonrpc_notification_factory(**kwargs):
    """
    vapi json rpc notification factory

    :type  method: :class:`str`
    :kwarg method: json rpc method
    :type  params: :class:`dict` or :class:`list` or None
    :kwarg params: json rpc method params

    :rtype: :class:`JsonRpcRequest`
    :return: json rpc request object
    """
    kwargs.pop('id', None)
    return vapi_jsonrpc_request_factory(**kwargs)


def vapi_jsonrpc_response_factory(request, **kwargs):
    """
    vapi json rpc response factory

    :type  request: :class:`JsonRpcRequest`
    :kwarg request: json rpc request object
    :type  kwargs: :class:`dict`
    :kwarg kwargs: See JsonRpc20Response for constructor parameters
    :rtype: :class:`JsonRpcResponse`
    :return: json rpc response object
    """
    if request is not None and request.notification:
        # Notification do not have response
        logger.error('JSON RPC notificaition should not have id')
        raise vapi_jsonrpc_error_invalid_params()

    jsonrpc_version = kwargs.get('jsonrpc', VAPI_JSONRPC_VERSION)
    # vapi json rpc supports version 2.0 only
    assert(jsonrpc_version == VAPI_JSONRPC_VERSION)
    kwargs.setdefault('jsonrpc', jsonrpc_version)
    kwargs.setdefault('id', None if request is None else request.id)
    return JsonRpc20Response(**kwargs)


def to_strkey_dict(dictionary):
    """
    Convert a unicode key dict into str key dict

    :type  dictionary: :class:`dict`
    :param dictionary: unicode dictionary
    :rtype: :class:`dict`
    :return: string key dict
    """
    result = {}
    for key, val in six.iteritems(dictionary):
        result[str(key)] = val
    return result


def deserialize_request(request_str):
    """
    Deserialize a json rpc request

    :type  request_str: :class:`str` or :class:`bytes:` or :class:`file`
    :param request_str: json rpc request str or a file like object
    :rtype: :class:`JsonRpcRequest`
    :return: json rpc request
    """
    # NYI: Vapi object directly from json string? Not easy with standard json
    #      deserializer

    try:
        # In 2.x, we get str from underlying layer and in 3.x,
        # we get bytes
        if isinstance(request_str, six.string_types):
            obj = json.loads(request_str, parse_float=decimal.Decimal)
        elif isinstance(request_str, six.binary_type):
            obj = json.loads(request_str.decode('utf-8'),
                             parse_float=decimal.Decimal)
        else:
            obj = json.load(request_str, parse_float=decimal.Decimal)
    except ValueError as err:
        logger.error('Deserialize request error %s', str(err))
        raise vapi_jsonrpc_error_parse_error(data=str(err))

    try:
        request = jsonrpc_request_factory(**to_strkey_dict(obj))
    except JsonRpcError as err:
        raise
    except Exception as err:
        logger.error('Invalid request %s', str(err))
        raise vapi_jsonrpc_error_invalid_request(data=str(err))

    if request is None:
        logger.error('Invalid request')
        raise vapi_jsonrpc_error_invalid_request()
    return request


def deserialize_response(response_str):
    """
    Deserialize a json rpc response

    :type  response_str: :class:`str` or :class:`bytes`
    :param response_str: json rpc response str
    :rtype: :class:`JsonRpcResponse`
    :return: json rpc response
    """
    # NYI: Vapi object directly from json string? Not easy with standard json
    #      deserializer

    try:
        # In 2.x, we get str from underlying layer and in 3.x,
        # we get bytes
        if isinstance(response_str, six.binary_type):
            response_str = response_str.decode('utf-8')
        obj = json.loads(response_str, parse_float=decimal.Decimal)
    except ValueError as err:
        logger.error('Deserialize response error %s', str(err))
        raise vapi_jsonrpc_error_parse_error(data=str(err))

    try:
        response = jsonrpc_response_factory(**to_strkey_dict(obj))
    except JsonRpcError as err:
        raise
    except Exception as err:
        logger.error('Invalid response %s', str(err))
        raise vapi_jsonrpc_error_invalid_request(data=str(err))

    if response is None:
        logger.error('Invalid response')
        raise vapi_jsonrpc_error_invalid_params()
    return response
