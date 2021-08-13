"""
String Constants used in vAPI runtime
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015-2019 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long


PARAMS = 'params'
SCHEME_ID = 'schemeId'
AUTHN_IDENTITY = 'authnIdentity'
EXECUTION_CONTEXT = 'ctx'
APPLICATION_CONTEXT = 'appCtx'
SECURITY_CONTEXT = 'securityCtx'
PROCESSORS = 'processors'
OPID = 'opId'
SHOW_UNRELEASED_APIS = '$showUnreleasedAPIs'
TASK_OPERATION = '$task'
TASK_ID = '$taskId'
TASK_REST_QUERY_PARAM = 'vmw-task'
REST_OP_ID_HEADER = 'X-Request-ID'

# Magic structure names
# Structure name for the StructValues that represent
# map entries in the runtime
MAP_ENTRY = 'map-entry'
# Structure name for the StructValue that represent
# maps when using cleanjson
MAP_STRUCT = 'map-struct'
# Structure name for the StructValues that represent
# operation input in the runtime
OPERATION_INPUT = 'operation-input'

# Structure name for the StructValue that represent
# a dynamic structure in the absence of the the type name
DYNAMIC_STRUCTURE = 'dynamic-structure'

# Constants for REST presentation Layer
JSONRPC = 'jsonrpc'
JSON_CONTENT_TYPE = 'application/json'
HTTP_ACCEPT_HEADER = 'Accept'
HTTP_USER_AGENT_HEADER = 'User-Agent'
HTTP_CONTENT_TYPE_HEADER = 'Content-Type'
HTTP_ACCEPT_LANGUAGE = 'accept-language'
HTTP_FORMAT_LOCALE = 'format-locale'
HTTP_TIMEZONE = 'timezone'
LOCALE = 'locale'

# HTTP headers
VAPI_ERROR_HEADER = 'vapi-error'
VAPI_HEADER_PREFIX = 'vapi-ctx-'
VAPI_SERVICE_HEADER = 'vapi-service'
VAPI_OPERATION_HEADER = 'vapi-operation'
VAPI_SESSION_HEADER = 'vmware-api-session-id'

header_mapping_dict = {
    'opid': 'opId',
    'actid': 'actId',
    '$showunreleasedapis': '$showUnreleasedAPIs',
    '$useragent': '$userAgent',
    '$donotroute': '$doNotRoute',
    'vmwaresessionid': 'vmwareSessionId',
    'activationid': 'ActivationId',
    '$taskid': '$taskId',
}


class Introspection(object):
    """
    String constants used in introsection service
    """
    PACKAGE = 'com.vmware.vapi.std.introspection'

    # Services
    PROVIDER_SVC = 'com.vmware.vapi.std.introspection.provider'
    SERVICE_SVC = 'com.vmware.vapi.std.introspection.service'
    OPERATION_SVC = 'com.vmware.vapi.std.introspection.operation'

    # Types
    DATA_DEFINITION = \
        'com.vmware.vapi.std.introspection.operation.data_definition'


class RestAnnotations(object):
    """
    String constants used in REST annotations in VMODL definition
    """
    REQUEST_MAPPING = 'RequestMapping'
    PATH_VARIABLE = 'PathVariable'
    QUERY_VARIABLE = 'Query'
    METHOD_ELEMENT = 'method'
    VALUE_ELEMENT = 'value'
    ACTION_PARAM = 'action'
    PARAMS_ELEMENT = 'params'
    PATH_ELEMENT = 'path'
    HEADERS_ELEMENT = 'headers'
    NAME_ELEMENT = 'name'
    RESPONSE_ELEMENT = 'Response'
    HEADER_ELEMENT = 'Header'
    BODY_ELEMENT = 'Body'
    VERB_GET = 'GET'
    VERB_POST = 'POST'
    VERB_PUT = 'PUT'
    VERB_PATCH = 'PATCH'
    VERB_DELETE = 'DELETE'


class RestAnnotationType(object):
    """
    Rest annotation type in VMODL definition
    """
    NONE = 0
    REQUEST = 1
    VERB = 2


class TaskType(object):
    """
    Task types
    """
    NONE = 0
    TASK = 1
    TASK_ONLY = 2
