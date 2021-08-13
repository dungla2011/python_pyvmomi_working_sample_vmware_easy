"""
REST Rule generator
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015-2018 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import collections
import six

from werkzeug.routing import Rule

from com.vmware.vapi.metadata.metamodel_client import Type
from vmware.vapi.bindings.task_helper import get_non_task_operation_name
from vmware.vapi.lib.constants import RestAnnotations, RestAnnotationType


# Mapping from HTTP method to operation name. The actual
# operation name might change based on ID parameters in the URL.
# Since GET is mapped to both list() and get(<>) operations,
# this map will return list as operation name and if the HTTP
# request has identifier arguments, then 'get' operation
# identifier should be used instead of 'list'.
http_method_map = {
    'GET': 'list',
    'PATCH': 'update',
    'DELETE': 'delete',
    'POST': 'create',
    'PUT': 'set',
    'HEAD': 'get'
}


class MappingRule(object):
    """
    Base class for all the mapping rules. This will contain
    the common helper functions for all the rules.
    """
    def __init__(self, rest_prefix):
        """
        Initialize MappingRule

        :type  rest_prefix: :class:`str`
        :param rest_prefix: REST URL prefix
        """
        self._rest_prefix = rest_prefix

    def _generate_service_base_url(self, service_id):
        """
        Generate base url for a particular service

        :type  service_id: :class:`str`
        :param service_id: Identifier of the service.
        :rtype: :class:`str`
        :return: base url for all the HTTP REST URLs for a given service.
        """
        suffix = service_id.replace('_', '-').replace('.', '/').lower()
        return '%s%s' % (self._rest_prefix, suffix)

    @staticmethod
    def _get_id_suffix(param_info_map):
        """
        Generate suffix using the ID parameters

        :type  param_info_map: :class:`collections.OrderedDict` of :class:`str`
               and :class:`com.vmware.vapi.metadata.metamodel_client.FieldInfo`
        :param param_info_map: Map of parameter name to its metamodel metadata
        :rtype: :class:`str` or `None`
        :return: string that can be used in the URL to represent an identifier,
            if there is no identifier, None is returned
        """
        for param_name, param_info in six.iteritems(param_info_map):
            if param_info.type.category == Type.Category.BUILTIN:
                if param_info.type.builtin_type == Type.BuiltinType.ID:
                    # TODO: Handle composite identifiers
                    return '/<string:%s>' % param_name
        # No ID parameter
        return ''


class ListMappingRule(MappingRule):
    """
    Mapping rule that handles 'list' operations in the API
    and generates HTTP GET.

    Operations matched:
    list() -> GET /svc
    """
    def __init__(self, rest_prefix):
        """
        Initialize ListMappingRule

        :type  rest_prefix: :class:`str`
        :param rest_prefix: REST URL prefix
        """
        MappingRule.__init__(self, rest_prefix)

    @staticmethod
    def match(operation_id, operation_summary):
        """
        Check if the given operation matches the criteria for this
        mapping rule.

        :type  operation_id: :class:`str`
        :param operation_id: Operation identifier
        :type  operation_summary:
        :class:`vmware.vapi.server.rest_handler.MetadataStore.OperationSummary`
        :param operation_summary: Details of the operation
        :rtype: :class:`bool`
        :return: True, if the given operation matches the criteria
            for this mapping rule, False, otherwise.
        """
        return bool(operation_id == 'list')

    def url(self, service_id, operation_id, operation_summary):
        """
        Generate the URL for the given operation

        :type  service_id: :class:`str`
        :param service_id: Service identifier
        :type  operation_id: :class:`str`
        :param operation_id: Operation identifier
        :type  operation_summary:
        :class:`vmware.vapi.server.rest_handler.MetadataStore.OperationSummary`
        :param operation_summary: Details of the operation
        :rtype: :class:`tuple` of :class:`str` and :class:`str`
        :return: Tuple that has URL and the HTTP method for the
            given operation.
        """
        service_url = self._generate_service_base_url(service_id)
        dispatch_info = DispatchInfo(
            mapping_type=RestAnnotationType.NONE,
            operation_id=get_non_task_operation_name(operation_id))
        return (service_url, 'GET', dispatch_info)


class PostMappingRule(MappingRule):
    """
    Mapping rule that handles 'create' operations in the API
    and generates HTTP POST.

    Operations matched:
    create() -> POST /svc
    create(...) -> POST /svc + body
    """
    def __init__(self, rest_prefix):
        """
        Initialize PostMappingRule

        :type  rest_prefix: :class:`str`
        :param rest_prefix: REST URL prefix
        """
        MappingRule.__init__(self, rest_prefix)

    @staticmethod
    def match(operation_id, operation_summary):
        """
        Check if the given operation matches the criteria for this
        mapping rule.

        :type  operation_id: :class:`str`
        :param operation_id: Operation identifier
        :type  operation_summary:
        :class:`vmware.vapi.server.rest_handler.MetadataStore.OperationSummary`
        :param operation_summary: Details of the operation
        :rtype: :class:`bool`
        :return: True, if the given operation matches the criteria
            for this mapping rule, False, otherwise.
        """
        return bool(operation_id == 'create')

    def url(self, service_id, operation_id, operation_summary):
        """
        Generate the URL for the given operation

        :type  service_id: :class:`str`
        :param service_id: Service identifier
        :type  operation_id: :class:`str`
        :param operation_id: Operation identifier
        :type  operation_summary:
        :class:`vmware.vapi.server.rest_handler.MetadataStore.OperationSummary`
        :param operation_summary: Details of the operation
        :rtype: :class:`tuple` of :class:`str` and :class:`str`
        :return: Tuple that has URL and the HTTP method for the
            given operation.
        """
        service_url = self._generate_service_base_url(service_id)
        dispatch_info = DispatchInfo(
            mapping_type=RestAnnotationType.NONE,
            operation_id=get_non_task_operation_name(operation_id))
        return (service_url, 'POST', dispatch_info)


class DeleteMappingRule(MappingRule):
    """
    Mapping rule that handles 'delete' operations in the API
    and generates HTTP DELETE.

    Operations matched:
    delete(ID id) -> DELETE /svc/<id>
    """
    def __init__(self, rest_prefix):
        """
        Initialize DeleteMappingRule

        :type  rest_prefix: :class:`str`
        :param rest_prefix: REST URL prefix
        """
        MappingRule.__init__(self, rest_prefix)

    @staticmethod
    def match(operation_id, operation_summary):
        """
        Check if the given operation matches the criteria for this
        mapping rule.

        :type  operation_id: :class:`str`
        :param operation_id: Operation identifier
        :type  operation_summary:
        :class:`vmware.vapi.server.rest_handler.MetadataStore.OperationSummary`
        :param operation_summary: Details of the operation
        :rtype: :class:`bool`
        :return: True, if the given operation matches the criteria
            for this mapping rule, False, otherwise.
        """
        return bool(operation_id == 'delete')

    def url(self, service_id, operation_id, operation_summary):
        """
        Generate the URL for the given operation

        :type  service_id: :class:`str`
        :param service_id: Service identifier
        :type  operation_id: :class:`str`
        :param operation_id: Operation identifier
        :type  operation_summary:
        :class:`vmware.vapi.server.rest_handler.MetadataStore.OperationSummary`
        :param operation_summary: Details of the operation
        :rtype: :class:`tuple` of :class:`str` and :class:`str`
        :return: Tuple that has URL and the HTTP method for the
            given operation.
        """
        service_url = self._generate_service_base_url(service_id)
        id_suffix = self._get_id_suffix(operation_summary.param_info_map)
        dispatch_info = DispatchInfo(
            mapping_type=RestAnnotationType.NONE,
            operation_id=get_non_task_operation_name(operation_id))
        if id_suffix:
            return (service_url + id_suffix, 'DELETE', dispatch_info)
        else:
            return (service_url, 'POST', dispatch_info)


class GetMappingRule(MappingRule):
    """
    Mapping rule that handles 'get' operations in the API
    and generates HTTP GET.

    Operations matched:
    get(ID id) -> GET /svc/<id>
    """
    def __init__(self, rest_prefix):
        """
        Initialize GetMappingRule

        :type  rest_prefix: :class:`str`
        :param rest_prefix: REST URL prefix
        """
        MappingRule.__init__(self, rest_prefix)

    @staticmethod
    def match(operation_id, operation_summary):
        """
        Check if the given operation matches the criteria for this
        mapping rule.

        :type  operation_id: :class:`str`
        :param operation_id: Operation identifier
        :type  operation_summary:
        :class:`vmware.vapi.server.rest_handler.MetadataStore.OperationSummary`
        :param operation_summary: Details of the operation
        :rtype: :class:`bool`
        :return: True, if the given operation matches the criteria
            for this mapping rule, False, otherwise.
        """
        return bool(operation_id == 'get')

    def url(self, service_id, operation_id, operation_summary):
        """
        Generate the URL for the given operation

        :type  service_id: :class:`str`
        :param service_id: Service identifier
        :type  operation_id: :class:`str`
        :param operation_id: Operation identifier
        :type  operation_summary:
        :class:`vmware.vapi.server.rest_handler.MetadataStore.OperationSummary`
        :param operation_summary: Details of the operation
        :rtype: :class:`tuple` of :class:`str` and :class:`str`
        :return: Tuple that has URL and the HTTP method for the
            given operation.
        """
        service_url = self._generate_service_base_url(service_id)
        id_suffix = self._get_id_suffix(operation_summary.param_info_map)
        dispatch_info = DispatchInfo(
            mapping_type=RestAnnotationType.NONE,
            operation_id=get_non_task_operation_name(operation_id))
        if id_suffix:
            return (service_url + id_suffix, 'GET', dispatch_info)
        else:
            return (service_url, 'POST', dispatch_info)


class PatchMappingRule(MappingRule):
    """
    Mapping rule that handles 'update' operations in the API
    and generates HTTP PATCH.

    Operations matched:
    update(ID id) -> PATCH /svc/<id>
    """
    def __init__(self, rest_prefix):
        """
        Initialize PatchMappingRule

        :type  rest_prefix: :class:`str`
        :param rest_prefix: REST URL prefix
        """
        MappingRule.__init__(self, rest_prefix)

    @staticmethod
    def match(operation_id, operation_summary):
        """
        Check if the given operation matches the criteria for this
        mapping rule.

        :type  operation_id: :class:`str`
        :param operation_id: Operation identifier
        :type  operation_summary:
        :class:`vmware.vapi.server.rest_handler.MetadataStore.OperationSummary`
        :param operation_summary: Details of the operation
        :rtype: :class:`bool`
        :return: True, if the given operation matches the criteria
            for this mapping rule, False, otherwise.
        """
        return bool(operation_id == 'update')

    def url(self, service_id, operation_id, operation_summary):
        """
        Generate the URL for the given operation

        :type  service_id: :class:`str`
        :param service_id: Service identifier
        :type  operation_id: :class:`str`
        :param operation_id: Operation identifier
        :type  operation_summary:
        :class:`vmware.vapi.server.rest_handler.MetadataStore.OperationSummary`
        :param operation_summary: Details of the operation
        :rtype: :class:`tuple` of :class:`str` and :class:`str`
        :return: Tuple that has URL and the HTTP method for the
            given operation.
        """
        service_url = self._generate_service_base_url(service_id)
        id_suffix = self._get_id_suffix(operation_summary.param_info_map)
        dispatch_info = DispatchInfo(
            mapping_type=RestAnnotationType.NONE,
            operation_id=get_non_task_operation_name(operation_id))
        if id_suffix:
            return (service_url + id_suffix, 'PATCH', dispatch_info)
        else:
            return (service_url, 'POST', dispatch_info)


class PutMappingRule(MappingRule):
    """
    Mapping rule that handles 'set' operations in the API
    and generates HTTP PUT.

    Operations matched:
    set(ID id) -> PUT /svc/<id>
    """
    def __init__(self, rest_prefix):
        """
        Initialize PutMappingRule

        :type  rest_prefix: :class:`str`
        :param rest_prefix: REST URL prefix
        """
        MappingRule.__init__(self, rest_prefix)

    @staticmethod
    def match(operation_id, operation_summary):
        """
        Check if the given operation matches the criteria for this
        mapping rule.

        :type  operation_id: :class:`str`
        :param operation_id: Operation identifier
        :type  operation_summary:
        :class:`vmware.vapi.server.rest_handler.MetadataStore.OperationSummary`
        :param operation_summary: Details of the operation
        :rtype: :class:`bool`
        :return: True, if the given operation matches the criteria
            for this mapping rule, False, otherwise.
        """
        return bool(operation_id == 'set')

    def url(self, service_id, operation_id, operation_summary):
        """
        Generate the URL for the given operation

        :type  service_id: :class:`str`
        :param service_id: Service identifier
        :type  operation_id: :class:`str`
        :param operation_id: Operation identifier
        :type  operation_summary:
        :class:`vmware.vapi.server.rest_handler.MetadataStore.OperationSummary`
        :param operation_summary: Details of the operation
        :rtype: :class:`tuple` of :class:`str` and :class:`str`
        :return: Tuple that has URL and the HTTP method for the
            given operation.
        """
        service_url = self._generate_service_base_url(service_id)
        id_suffix = self._get_id_suffix(operation_summary.param_info_map)
        dispatch_info = DispatchInfo(
            mapping_type=RestAnnotationType.NONE,
            operation_id=get_non_task_operation_name(operation_id))
        if id_suffix:
            return (service_url + id_suffix, 'PUT', dispatch_info)
        else:
            return (service_url, 'POST', dispatch_info)


class PostActionMappingRule(MappingRule):
    """
    Mapping rule that handles non-crud operations in the API
    and generates HTTP POST.

    Operations matched:
    custom() -> POST /svc?~action=custom
    custom(ID id) -> POST /svc/<id>?~action=custom
    custom(...) -> POST /svc?~action=custom + body
    custom(ID id, ...) -> POST /svc/<id>?~action=custom + body
    """
    _crud_ops = ['create', 'get', 'list', 'update', 'set', 'delete']

    def __init__(self, rest_prefix):
        """
        Initialize PostActionMappingRule

        :type  rest_prefix: :class:`str`
        :param rest_prefix: REST URL prefix
        """
        MappingRule.__init__(self, rest_prefix)

    @staticmethod
    def match(operation_id, operation_summary):
        """
        Check if the given operation matches the criteria for this
        mapping rule.

        :type  operation_id: :class:`str`
        :param operation_id: Operation identifier
        :type  operation_summary:
        :class:`vmware.vapi.server.rest_handler.MetadataStore.OperationSummary`
        :param operation_summary: Details of the operation
        :rtype: :class:`bool`
        :return: True, if the given operation matches the criteria
            for this mapping rule, False, otherwise.
        """
        return bool(operation_id not in PostActionMappingRule._crud_ops)

    def url(self, service_id, operation_id, operation_summary):
        """
        Generate the URL for the given operation

        :type  service_id: :class:`str`
        :param service_id: Service identifier
        :type  operation_id: :class:`str`
        :param operation_id: Operation identifier
        :type  operation_summary:
        :class:`vmware.vapi.server.rest_handler.MetadataStore.OperationSummary`
        :param operation_summary: Details of the operation
        :rtype: :class:`tuple` of :class:`str` and :class:`str`
        :return: Tuple that has URL and the HTTP method for the
            given operation.
        """
        service_url = self._generate_service_base_url(service_id)
        id_suffix = self._get_id_suffix(operation_summary.param_info_map)
        dispatch_info = DispatchInfo(
            mapping_type=RestAnnotationType.NONE,
            operation_id=get_non_task_operation_name(operation_id))
        return (service_url + id_suffix, 'POST', dispatch_info)


class CustomRequestMappingRule(MappingRule):
    """
    Mapping rule that handles custom @RequestMapping annotations in the API
    Processing only "value", "method" and "params" (only action=) elements
    from the RequestMapping annotation

    Operation definition:
    @RequestMapping(value="/svc/{id}?action=custom",
                    method=RequestMethod.POST,
                    contentType="...",
                    accept="...")
    @ResponseStatus(204)
    void custom(@PathVariable("user_id") ID id, ...)

    Generated mapping: POST /svc/{id}?action=custom [+ body]
    """
    def __init__(self, rest_prefix):
        """
        Initialize CustomRequestsMappingRule

        :type  rest_prefix: :class:`str`
        :param rest_prefix: REST URL prefix
        """
        MappingRule.__init__(self, rest_prefix)

    @staticmethod
    def match(operation_id, operation_summary):
        """
        Check if the given operation matches the criteria for this
        mapping rule.

        :type  operation_id: :class:`str`
        :param operation_id: Operation identifier
        :type  operation_summary:
        :class:`vmware.vapi.server.rest_handler.MetadataStore.OperationSummary`
        :param operation_summary: Details of the operation
        :rtype: :class:`bool`
        :return: True, if the given operation matches the criteria
            for this mapping rule, False, otherwise.
        """
        return bool(operation_summary.has_request_mapping_metadata())

    def url(self, service_id, operation_id, operation_summary):
        """
        Generate the mapping rule for an operation that has RequestMapping
        in the VMODL2 service definition.
        :type  service_id: :class:`str`
        :param service_id: Service identifier
        :type  operation_id: :class:`str`
        :param operation_id: Operation identifier
        :type  operation_summary:
        :class:`vmware.vapi.server.rest_handler.MetadataStore.OperationSummary`
        :param operation_summary: Details of the operation
        :rtype: :class:`tuple` of :class:`str` and :class:`str`
        :return: Tuple that has URL and the HTTP method for the
            given operation.
        """
        request_mapping = operation_summary.request_mapping_metadata
        http_method = request_mapping.elements[
            RestAnnotations.METHOD_ELEMENT].string_value

        custom_url = request_mapping.elements[
            RestAnnotations.VALUE_ELEMENT].string_value
        custom_url = custom_url.replace('{', '<')
        custom_url = custom_url.replace('}', '>')
        custom_url = '%s%s' % (self._rest_prefix, custom_url[1:])

        # Get value of fixed query parameter 'action' if it exists
        if '?' in custom_url:
            (custom_url, param) = custom_url.split('?')
            (_, action_value) = param.split('=')
        else:
            params = request_mapping.elements.get(
                RestAnnotations.PARAMS_ELEMENT)
            if params and params.list_value:
                action_value = None
                for param in params.list_value:
                    param_split = param.split('=')
                    if (len(param_split) == 2
                            and param_split[0] == RestAnnotations.ACTION_PARAM):
                        action_value = param_split[1]
                        break

            else:
                action_value = None

        dispatch_info = DispatchInfo(
            mapping_type=RestAnnotationType.REQUEST,
            operation_id=get_non_task_operation_name(operation_id),
            action_value=action_value)

        return (custom_url, http_method, dispatch_info)


class VerbMappingRule(MappingRule):
    """
    Mapping rule that handles @Verb annotations in the API

    Operation definition:
    @GET(path="/svc/op", params="myquery=value",
         headers="content-type:application/json")
    String get()
    """
    def __init__(self, rest_prefix):
        """
        Initialize VerbMappingRule

        :type  rest_prefix: :class:`str`
        :param rest_prefix: REST URL prefix
        """
        MappingRule.__init__(self, rest_prefix)

    @staticmethod
    def match(operation_id, operation_summary):
        """
        Check if the given operation matches the criteria for this
        mapping rule.

        :type  operation_id: :class:`str`
        :param operation_id: Operation identifier
        :type  operation_summary
        :class:`vmware.vapi.server.rest_handler.MetadataStore.OperationSummary`
        :param operation_summary: Details of the operation
        :rtype: :class:`bool`
        :return: True, if the given operation matches the criteria
            for this mapping rule, False, otherwise.
        """
        return bool(operation_summary.has_verb_metadata())

    def url(self, service_id, operation_id, operation_summary):
        """
        Generate the URL for the given operation

        :type  service_id: :class:`str`
        :param service_id: Service identifier
        :type  operation_id: :class:`str`
        :param operation_id: Operation identifier
        :type  operation_summary:
        :class:`vmware.vapi.server.rest_handler.MetadataStore.OperationSummary`
        :param operation_summary: Details of the operation
        :type  param_info_map: :class:`collections.OrderedDict` of :class:`str`
               and :class:`com.vmware.vapi.metadata.metamodel_client.FieldInfo`
        :return: Tuple that has URL and the HTTP method for the
            given operation.
        """
        http_method, request_metadata = \
            next(iter(operation_summary.verb_metadata.items()))

        custom_url = request_metadata.elements[
            RestAnnotations.PATH_ELEMENT].string_value
        custom_url = custom_url.replace('{', '<')
        custom_url = custom_url.replace('}', '>')
        custom_url = '%s%s' % (self._rest_prefix, custom_url[1:])

        dispatch_params = request_metadata.elements.get(
            RestAnnotations.PARAMS_ELEMENT)
        if dispatch_params is not None:
            dispatch_params = dispatch_params.list_value
        dispatch_headers = request_metadata.elements.get(
            RestAnnotations.HEADERS_ELEMENT)
        if dispatch_headers is not None:
            dispatch_headers = dispatch_headers.list_value

        dispatch_info = DispatchInfo(
            mapping_type=RestAnnotationType.VERB,
            operation_id=get_non_task_operation_name(operation_id),
            params=dispatch_params,
            headers=dispatch_headers
        )

        return (custom_url, http_method, dispatch_info)


class DispatchInfo(object):
    """
    Class to hold the request dispatch related information
    """
    def __init__(self, mapping_type, operation_id, params=None,
                 headers=None, action_value=None):
        self.mapping_type = mapping_type
        self.operation_id = operation_id
        self.params = params if params else []
        self.headers = headers if headers else []
        self.action_value = action_value

    def _default_matching(self, http_method, query_params, uri_params):
        """
        Check if dispatch info matches based on the HTTP method, the
        identifier arguments in the URL and the query string.

        :type  http_method: :class:`str`
        :param http_method: HTTP request method
        :type  query_params: :class:`dict` of :class:`str` and :class:`object`
        :param query_params: Decoded dictionary from the query string
        :type  uri_params: :class:`dict` of :class:`str` and :class:`object`
        :param uri_params: Arguments parsed from the HTTP URL
        :rtype: :class:`str` and :class:`int`
        :return: If operation matched and arity
        """
        operation_id = http_method_map[http_method]
        # If ID is in the URI parameter then, operation_id is get instead of
        # list
        if uri_params and operation_id == 'list':
            ## TODO: Handle composite identifier case
            operation_id = 'get'
        action = query_params.get('~action')
        if action:
            operation_id = action.replace('-', '_')
        return operation_id == self.operation_id, 1

    def _request_matching(self, http_method, query_params, uri_params):
        """
        Check if dispatch info matches based on the action parameter in the
        query string

        :type  http_method: :class:`str`
        :param http_method: HTTP request method
        :type  query_params: :class:`dict` of :class:`str` and :class:`object`
        :param query_params: Decoded dictionary from the query string
        :type  uri_params: :class:`dict` of :class:`str` and :class:`object`
        :param uri_params: Arguments parsed from the HTTP URL
        :rtype: :class:`bool` and :class:`int`
        :return: If operation matched and arity
        """
        action_requested = query_params.get(RestAnnotations.ACTION_PARAM)
        if action_requested:
            return action_requested == self.action_value, 1
        else:
            return self._default_matching(http_method, query_params, uri_params)

    def _verb_matching(self, query_params, headers):
        """
        Check if dispatch info matches the given request

        :type  query_params: :class:`dict` of :class:`str` and :class:`object`
        :param query_params: Decoded dictionary from the query string
        :rtype: :class:`bool` and :class:`int`
        :return: If operation matched and arity
        """
        arity = 0
        # Iterating over the dispatch parameters
        for param in self.params:
            match = None
            # Escape the single quote
            param.replace("'", "\\'")
            param_split = param.split('=')
            # For every query param match increase arity by 3
            if param_split[0].strip() in query_params:
                arity += 3
                match = True
            else:
                # For each param not in query param decrease arity by 1
                arity -= 1

            if len(param_split) > 1:
                q_val = query_params.get(param_split[0].strip())
                # For query param value match increase arity by 4
                if q_val == param_split[1]:
                    arity += 4
                elif match and param_split[1]:
                    # If param is present in query params but the param
                    # value in dispatch is not equal to that in query params
                    # match fails
                    match = False

            if match is False:
                return False, arity

        # Iterating over the dispatch headers
        for header in self.headers:
            match = None
            # Escape the single quote
            header.replace("'", "\\'")
            header_split = header.split(':')
            # For each header match increase arity by 1
            if header_split[0].lower() in headers:
                arity += 1
                match = True
            else:
                # For each header mismatch decrease arity by 1
                arity -= 1

            if len(header_split) > 1:
                header_split[1] = ','.join([
                    x.strip() for x in header_split[1].split(',')])
                header_val = headers.get(header_split[0].strip())
                if header_val:
                    header_val = ','.join([
                        x.strip() for x in header_val.split(',')])
                # For each header value match increase arity by 2
                if header_val and header_val.find(header_split[1]) >= 0:
                    arity += 2
                    match = True
                elif match and header_split[1]:
                    # For header value mismatch match fails
                    match = False

            if match is False:
                return False, arity

        return True, arity

    def get_operation_id(self, request, query_params, uri_params):
        """
        Get the matching operation id and arity based upon request

        :type  request: :class:`werkzeug.wrappers.Request`
        :param request: Request object
        :type  query_params: :class:`dict` of :class:`str` and :class:`object`
        :param query_params: Decoded dictionary from the query string
        :type  uri_params: :class:`dict` of :class:`str` and :class:`object`
        :param uri_params: Arguments parsed from the HTTP URL
        :rtype: :class:`str` and :class:`int`
        :return: Identifier of operation matched, arity and mapping type
        """
        arity = 0
        if self.mapping_type == RestAnnotationType.VERB:
            retval, arity = self._verb_matching(query_params,
                                                request.headers)
        elif self.mapping_type == RestAnnotationType.REQUEST:
            # Fixed query param 'action' is supported only for
            # HTTP POST method
            # Delete 'action' from query string if:
            # 1) We start supporting 'action' for GET or,
            # 2) We start accepting query parameters for POST
            # Only in those cases, the 'action' parameter in query string
            # would cause an unexpected keyword argument error
            retval, arity = self._request_matching(request.method,
                                                   query_params, uri_params)
        else:
            retval, arity = self._default_matching(request.method,
                                                   query_params, uri_params)

        return self.operation_id if retval else None, arity, self.mapping_type

    def __eq__(self, other):
        if other is None or not isinstance(other, DispatchInfo):
            return False

        for attr in six.iterkeys(vars(self)):
            if getattr(self, attr) != getattr(other, attr):
                return False

        return True

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        class_name = self.__class__.__name__
        attrs = six.iterkeys(vars(self))
        result = ', '.join(
            ['%s=%s' % (attr, repr(getattr(self, attr)))
             for attr in attrs])
        return '%s(%s)' % (class_name, result)

    def __str__(self):
        attrs = six.iterkeys(vars(self))
        result = ', '.join(
            ['%s : %s' % (attr, str(getattr(self, attr)))
             for attr in attrs])
        return '{%s}' % result

    def __hash__(self):
        return str(self).__hash__()


class RoutingRuleGenerator(object):
    """
    Generate the routing rules based on vAPI metamodel metadata.
    """
    def __init__(self, metadata, rest_prefix):
        """
        Initialize RoutingRuleGenerator

        :type  metadata: :class:`vmware.vapi.server.rest_handler.MetadataStore`
        :param metadata: Object that contains the relevant metamodel metadata of
            all the services.
        :type  rest_prefix: :class:`str`
        :param rest_prefix: REST URL prefix
        """
        self._metadata = metadata

        if not rest_prefix.endswith('/'):
            self._rest_prefix = '%s/' % rest_prefix
        else:
            self._rest_prefix = rest_prefix
        self._mapping_rules = [
            CustomRequestMappingRule(self._rest_prefix),
            VerbMappingRule(self._rest_prefix),
            ListMappingRule(self._rest_prefix),
            PostMappingRule(self._rest_prefix),
            DeleteMappingRule(self._rest_prefix),
            GetMappingRule(self._rest_prefix),
            PatchMappingRule(self._rest_prefix),
            PutMappingRule(self._rest_prefix),
            PostActionMappingRule(self._rest_prefix),
        ]

    def generate_mapping_rule(
            self, service_id, operation_id, operation_summary):
        """
        Generate HTTP REST rule from operation summary

        :type  service_id: :class:`str`
        :param service_id: Identifier of the service
        :type  operation_id: :class:`str`
        :param operation_id: Identifier of the operation
        :type  operation_summary:
        :class:`vmware.vapi.server.rest_handler.MetadataStore.OperationSummary`
        :param operation_summary: Details of the operation
        :rtype: :class:`tuple` of :class:`str`, :class:`str` and one
            :class:`dict` element
        :return: Tuple that has URL, HTTP method and dispatch info for the given
            operation.

        Dispatch info is a mapping from value of fixed query
        parameter 'action' and corresponding operation_id.
        The possible cases for REST mapping and dispatching are:
        1) Operation with fixed action param:
            @RequestMapping(value="/svc/{id}?action=custom",
                           method=RequestMethod.POST)
            dispatch_info = {<action> : <operation_id>}
            <action> parameter in the query string would be used to obtain the
            operation_id for request dispatching
        2) Operation with @RequestMapping but no fixed param
            @RequestMapping(value="/svc/{id}", method=...)
            dispatch_info = {None: <operation_id>}
            Request can be dispatched to operation_id. Assuming there are no
            conflicting REST mappings
        3) Default REST mapping
            dispatch_info = {None: None}
            Operation ID would be determined based on HTTP method, path params
            and query params
        """
        for mapping_rule in self._mapping_rules:
            if service_id == 'com.vmware.cis.session' and type(mapping_rule) == VerbMappingRule:
                continue

            if mapping_rule.match(operation_id, operation_summary):
                return mapping_rule.url(service_id, operation_id,
                                        operation_summary)

        return None

    @property
    def rest_rules(self):
        """
        HTTP REST rules

        :rtype: :class:` `list` of :class:`werkzeug.routing.Rule`
        :return: List of HTTP REST rules for all the registered services
        """

        rules_dict = collections.defaultdict(list)

        for service_id, service_info in six.iteritems(
                self._metadata.service_map):
            for operation_id, operation_summary in six.iteritems(service_info):
                (service_url, http_method, dispatch_info) = \
                    self.generate_mapping_rule(service_id,
                                               operation_id,
                                               operation_summary)
                # dispatch_info's for service_url's are aggregated to generate
                # the Werkzeug 'endpoint' which would be used to dispatch the
                # request
                rules_dict[(service_id,
                            service_url,
                            http_method)].append(dispatch_info)

        rules = [Rule(service_url,
                      endpoint=(service_id, tuple(dispatch_info)),
                      methods=[http_method])
                 for (service_id, service_url, http_method), dispatch_info in
                 rules_dict.items()]

        return rules
