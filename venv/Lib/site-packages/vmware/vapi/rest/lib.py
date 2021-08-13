"""
Util classes for HTTP/REST
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long


# pylint: disable=C0103
class HTTPStatusCodes(object):
    """
    Constants for HTTP status codes
    """
    HTTP_200_OK = 200
    HTTP_201_CREATED = 201
    HTTP_202_ACCEPTED = 202
    HTTP_204_NO_CONTENT = 204
    HTTP_304_NOT_MODIFIED = 304
    HTTP_400_BAD_REQUEST = 400
    HTTP_401_UNAUTHORIZED = 401
    HTTP_402_PAYMENT_REQUIRED = 402
    HTTP_403_FORBIDDEN = 403
    HTTP_404_NOT_FOUND = 404
    HTTP_405_METHOD_NOT_ALLOWED = 405
    HTTP_406_NOT_ACCEPTABLE = 406
    HTTP_407_PROXY_AUTHENTICATION_REQUIRED = 407
    HTTP_408_REQUEST_TIMEOUT = 408
    HTTP_409_CONFLICT = 409
    HTTP_410_GONE = 410
    HTTP_411_LENGTH_REQUIRED = 411
    HTTP_412_PRECONDITION_FAILED = 412
    HTTP_413_REQUEST_ENTITY_TOO_LARGE = 413
    HTTP_414_REQUEST_URI_TOO_LARGE = 414
    HTTP_415_UNSUPPORTED_MEDIA_TYPE = 415
    HTTP_416_REQUEST_RANGE_NOT_SATISFIABLE = 416
    HTTP_417_EXPECTATION_FAILED = 417
    HTTP_418_IM_A_TEAPOT = 418
    HTTP_422_UNPROCESSABLE_ENTITY = 422
    HTTP_423_LOCKED = 423
    HTTP_424_FAILED_DEPENDENCY = 424
    HTTP_426_UPGRADE_REQUIRED = 426
    HTTP_428_PRECONDITION_REQUIRED = 428
    HTTP_429_TOO_MANY_REQUESTS = 429
    HTTP_431_REQUEST_HEADER_FIELDS_TOO_LARGE = 431
    HTTP_500_INTERNAL_SERVER_ERROR = 500
    HTTP_501_NOT_IMPLEMENTED = 501
    HTTP_503_SERVICE_UNAVAILABLE = 503
    HTTP_504_GATEWAY_TIMEOUT = 504
    HTTP_505_HTTP_VERSION_NOT_SUPPORTED = 505
    HTTP_506_VARIANT_ALSO_NEGOTIATES = 506
    HTTP_507_INSUFFICIENT_STORAGE = 507
    HTTP_508_LOOP_DETECTED = 508
    HTTP_509_BANDWIDTH_LIMIT_EXCEEDED = 509
    HTTP_510_NOT_EXTENDED = 510
    HTTP_511_NETWORK_AUTHENTICATION_REQUIRED = 511


# Mapping of vAPI standard errors to HTTP error codes:
# https://wiki.eng.vmware.com/VAPI/Specs/VMODL2toREST/Reference/REST-error-mapping
vapi_to_http_error_map = {
    'com.vmware.vapi.std.errors.already_exists':
        HTTPStatusCodes.HTTP_400_BAD_REQUEST,
    'com.vmware.vapi.std.errors.already_in_desired_state':
        HTTPStatusCodes.HTTP_400_BAD_REQUEST,
    'com.vmware.vapi.std.errors.feature_in_use':
        HTTPStatusCodes.HTTP_400_BAD_REQUEST,
    'com.vmware.vapi.std.errors.internal_server_error':
        HTTPStatusCodes.HTTP_500_INTERNAL_SERVER_ERROR,
    'com.vmware.vapi.std.errors.invalid_argument':
        HTTPStatusCodes.HTTP_400_BAD_REQUEST,
    'com.vmware.vapi.std.errors.invalid_element_configuration':
        HTTPStatusCodes.HTTP_400_BAD_REQUEST,
    'com.vmware.vapi.std.errors.invalid_element_type':
        HTTPStatusCodes.HTTP_400_BAD_REQUEST,
    'com.vmware.vapi.std.errors.invalid_request':
        HTTPStatusCodes.HTTP_400_BAD_REQUEST,
    'com.vmware.vapi.std.errors.not_found':
        HTTPStatusCodes.HTTP_404_NOT_FOUND,
    'com.vmware.vapi.std.errors.not_allowed_in_current_state':
        HTTPStatusCodes.HTTP_400_BAD_REQUEST,
    'com.vmware.vapi.std.errors.operation_not_found':
        HTTPStatusCodes.HTTP_404_NOT_FOUND,
    'com.vmware.vapi.std.errors.resource_busy':
        HTTPStatusCodes.HTTP_400_BAD_REQUEST,
    'com.vmware.vapi.std.errors.resource_in_use':
        HTTPStatusCodes.HTTP_400_BAD_REQUEST,
    'com.vmware.vapi.std.errors.resource_inaccessible':
        HTTPStatusCodes.HTTP_400_BAD_REQUEST,
    'com.vmware.vapi.std.errors.concurrent_change':
        HTTPStatusCodes.HTTP_409_CONFLICT,
    'com.vmware.vapi.std.errors.service_unavailable':
        HTTPStatusCodes.HTTP_503_SERVICE_UNAVAILABLE,
    'com.vmware.vapi.std.errors.timed_out':
        HTTPStatusCodes.HTTP_504_GATEWAY_TIMEOUT,
    'com.vmware.vapi.std.errors.unable_to_allocate_resource':
        HTTPStatusCodes.HTTP_400_BAD_REQUEST,
    'com.vmware.vapi.std.errors.unauthenticated':
        HTTPStatusCodes.HTTP_401_UNAUTHORIZED,
    'com.vmware.vapi.std.errors.unauthorized':
        HTTPStatusCodes.HTTP_403_FORBIDDEN,
    'com.vmware.vapi.std.errors.unsupported':
        HTTPStatusCodes.HTTP_400_BAD_REQUEST,
}


# Mapping of HTTP error codes to vAPI standard errors:
# https://wiki.eng.vmware.com/VAPI/Specs/REST/error_mapping
http_to_vapi_error_map = {
    HTTPStatusCodes.HTTP_400_BAD_REQUEST:
        'com.vmware.vapi.std.errors.invalid_request',
    HTTPStatusCodes.HTTP_401_UNAUTHORIZED:
        'com.vmware.vapi.std.errors.unauthenticated',
    HTTPStatusCodes.HTTP_402_PAYMENT_REQUIRED:
        'com.vmware.vapi.std.errors.unauthorized',
    HTTPStatusCodes.HTTP_403_FORBIDDEN:
        'com.vmware.vapi.std.errors.unauthorized',
    HTTPStatusCodes.HTTP_404_NOT_FOUND:
        'com.vmware.vapi.std.errors.not_found',
    HTTPStatusCodes.HTTP_405_METHOD_NOT_ALLOWED:
        'com.vmware.vapi.std.errors.invalid_request',
    HTTPStatusCodes.HTTP_406_NOT_ACCEPTABLE:
        'com.vmware.vapi.std.errors.invalid_request',
    HTTPStatusCodes.HTTP_407_PROXY_AUTHENTICATION_REQUIRED:
        'com.vmware.vapi.std.errors.unauthenticated',
    HTTPStatusCodes.HTTP_408_REQUEST_TIMEOUT:
        'com.vmware.vapi.std.errors.timed_out',
    HTTPStatusCodes.HTTP_409_CONFLICT:
        'com.vmware.vapi.std.errors.concurrent_change',
    HTTPStatusCodes.HTTP_410_GONE:
        'com.vmware.vapi.std.errors.not_found',
    HTTPStatusCodes.HTTP_411_LENGTH_REQUIRED:
        'com.vmware.vapi.std.errors.invalid_request',
    HTTPStatusCodes.HTTP_412_PRECONDITION_FAILED:
        'com.vmware.vapi.std.errors.invalid_request',
    HTTPStatusCodes.HTTP_413_REQUEST_ENTITY_TOO_LARGE:
        'com.vmware.vapi.std.errors.invalid_request',
    HTTPStatusCodes.HTTP_414_REQUEST_URI_TOO_LARGE:
        'com.vmware.vapi.std.errors.invalid_request',
    HTTPStatusCodes.HTTP_415_UNSUPPORTED_MEDIA_TYPE:
        'com.vmware.vapi.std.errors.invalid_request',
    HTTPStatusCodes.HTTP_416_REQUEST_RANGE_NOT_SATISFIABLE:
        'com.vmware.vapi.std.errors.resource_inaccessible',
    HTTPStatusCodes.HTTP_417_EXPECTATION_FAILED:
        'com.vmware.vapi.std.errors.invalid_request',
    HTTPStatusCodes.HTTP_418_IM_A_TEAPOT:
        'com.vmware.vapi.std.errors.error',
    HTTPStatusCodes.HTTP_422_UNPROCESSABLE_ENTITY:
        'com.vmware.vapi.std.errors.invalid_request',
    HTTPStatusCodes.HTTP_423_LOCKED:
        'com.vmware.vapi.std.errors.resource_busy',
    HTTPStatusCodes.HTTP_424_FAILED_DEPENDENCY:
        'com.vmware.vapi.std.errors.invalid_request',
    HTTPStatusCodes.HTTP_426_UPGRADE_REQUIRED:
        'com.vmware.vapi.std.errors.invalid_request',
    HTTPStatusCodes.HTTP_428_PRECONDITION_REQUIRED:
        'com.vmware.vapi.std.errors.concurrent_change',
    HTTPStatusCodes.HTTP_429_TOO_MANY_REQUESTS:
        'com.vmware.vapi.std.errors.service_unavailable',
    HTTPStatusCodes.HTTP_431_REQUEST_HEADER_FIELDS_TOO_LARGE:
        'com.vmware.vapi.std.errors.invalid_request',
    HTTPStatusCodes.HTTP_500_INTERNAL_SERVER_ERROR:
        'com.vmware.vapi.std.errors.internal_server_error',
    HTTPStatusCodes.HTTP_501_NOT_IMPLEMENTED:
        'com.vmware.vapi.std.errors.error',
    HTTPStatusCodes.HTTP_503_SERVICE_UNAVAILABLE:
        'com.vmware.vapi.std.errors.service_unavailable',
    HTTPStatusCodes.HTTP_504_GATEWAY_TIMEOUT:
        'com.vmware.vapi.std.errors.timed_out',
    HTTPStatusCodes.HTTP_505_HTTP_VERSION_NOT_SUPPORTED:
        'com.vmware.vapi.std.errors.invalid_request',
    HTTPStatusCodes.HTTP_506_VARIANT_ALSO_NEGOTIATES:
        'com.vmware.vapi.std.errors.internal_server_error',
    HTTPStatusCodes.HTTP_507_INSUFFICIENT_STORAGE:
        'com.vmware.vapi.std.errors.unable_to_allocate_resource',
    HTTPStatusCodes.HTTP_508_LOOP_DETECTED:
        'com.vmware.vapi.std.errors.internal_server_error',
    HTTPStatusCodes.HTTP_509_BANDWIDTH_LIMIT_EXCEEDED:
        'com.vmware.vapi.std.errors.unable_to_allocate_resource',
    HTTPStatusCodes.HTTP_510_NOT_EXTENDED:
        'com.vmware.vapi.std.errors.invalid_request',
    HTTPStatusCodes.HTTP_511_NETWORK_AUTHENTICATION_REQUIRED:
        'com.vmware.vapi.std.errors.unauthenticated',
}

# List of HTTP status codes representing successful operations
successful_status_codes = [
    HTTPStatusCodes.HTTP_200_OK,
    HTTPStatusCodes.HTTP_201_CREATED,
    HTTPStatusCodes.HTTP_202_ACCEPTED,
    HTTPStatusCodes.HTTP_204_NO_CONTENT,
    HTTPStatusCodes.HTTP_304_NOT_MODIFIED,
]
