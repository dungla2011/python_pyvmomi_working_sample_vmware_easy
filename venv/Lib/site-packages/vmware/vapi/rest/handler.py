"""
REST Handler for WSGI application
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015-2020 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import base64
import collections
import decimal
import json
import six
import werkzeug

from com.vmware.vapi.metadata.metamodel_client import (
    Component, Structure, Type, Enumeration,
    GenericInstantiation, StructureInfo)
from vmware.vapi.bindings.task_helper import get_task_operation_name
from vmware.vapi.common.context import set_context, clear_context
from vmware.vapi.core import ApplicationContext, ExecutionContext
from vmware.vapi.data.serializers.cleanjson import DataValueConverter
from vmware.vapi.data.type import Type as DataType
from vmware.vapi.data.value import (
    data_value_factory, ListValue, StructValue,
    StringValue, OptionalValue, VoidValue, SecretValue)
from vmware.vapi.lib.constants import (
    HTTP_ACCEPT_LANGUAGE, HTTP_FORMAT_LOCALE, HTTP_TIMEZONE, LOCALE,
    MAP_ENTRY, OPERATION_INPUT, OPID, RestAnnotations,
    RestAnnotationType, REST_OP_ID_HEADER, TASK_REST_QUERY_PARAM)
from vmware.vapi.lib.context import create_default_application_context
from vmware.vapi.lib.load import dynamic_import_list
from vmware.vapi.lib.log import get_vapi_logger
from vmware.vapi.protocol.client.local_connector import get_local_connector
from vmware.vapi.security.session import (
    REST_SESSION_ID_KEY, REQUIRE_HEADER_AUTHN)
from vmware.vapi.stdlib.client.factories import StubConfigurationFactory
from vmware.vapi.exception import CoreException

from .lib import vapi_to_http_error_map
from .rules import RoutingRuleGenerator

logger = get_vapi_logger(__name__)


class MetadataStore(object):
    """
    Helper class to process the metamodel metadata and
    provide a convenient way to access the data.
    """

    class OperationSummary(object):
        """
        Helper class to contain only useful metamodel metadata of an operation
        """
        def __init__(self, param_info_map, path_variables_map=None,
                     request_mapping_metadata=None, verb_metadata=None,
                     query_variables_map=None, header_variables_map=None,
                     success_reponse_code=None, response_headers_map=None,
                     response_body_name=None):
            """
            :type  param_info_map:
                :class:`collections.OrderedDict` of :class:`str` and
                :class:`com.vmware.vapi.metadata.metamodel_client.FieldInfo`
            :param param_info_map: Map of parameter name to its metamodel
                metadata
            :type  path_variables_map: :class:`dict` of :class:`str` and
                :class:`str`
            :param path_variables_map: Map of path variable name to canonical
                name of the parameters that have the PathVariable annotation
            :type  request_mapping_metadata:
                :class:`com.vmware.vapi.metadata.metamodel_provider.ElementMap`
            :param request_mapping_metadata: Metamodel metadata of
                RequestMapping annotation on the operation
            :type  verb_metadata:
                :class:`com.vmware.vapi.metadata.metamodel_provider.ElementMap`
            :param verb_metadata: Metamodel metadata of
                Verb annotation on the operation
            :type  query_variables_map:
                :class:`com.vmware.vapi.metadata.metamodel_provider.ElementMap`
            :param query_variables_map: Metamodel metadata of
                dispatch query variable in Verb annotation on the operation
            :type  header_variables_map:
                :class:`com.vmware.vapi.metadata.metamodel_provider.ElementMap`
            :param header_variables_map: Metamodel metadata of
                dispatch header variable in Verb annotation on the operation
            :type  success_reponse_code:
                :class:`int`
            :param success_response_code: Response code for success
            :type  response_headers_map:
                :class:`dict` of :class:`str` and :class:`str`
            :param response_headers_map: Map of response field name to
                http header name
            :type  response_body_name:
                :class:`str`
            :param response_body_name: Response field name has
                Body annotation, will only return the value of the field
            """
            self.param_info_map = param_info_map
            self.path_variables_map = path_variables_map
            self.request_mapping_metadata = request_mapping_metadata
            self.verb_metadata = verb_metadata
            self.query_variables_map = query_variables_map
            self.header_variables_map = header_variables_map
            self.success_response_code = success_reponse_code
            self.response_headers_map = response_headers_map
            self.response_body_name = response_body_name

        def has_request_mapping_metadata(self):
            """
            Tells whether this operation has RequestMapping annotation
            """
            return self.request_mapping_metadata is not None

        def has_verb_metadata(self):
            """
            Tells whether this operation has Verb annotation
            """
            return self.verb_metadata is not None

    def __init__(self, api_provider):
        """
        Initialize MetadataStore

        :type  api_provider: :class:`vmware.vapi.core.ApiProvider`
        :param api_provider: ApiProvider to get the metadata
        """
        self.structure_map = {}
        self.enumeration_map = {}
        self.service_map = {}
        # Map of {struct_id: {error_id: {code: http_status, reason: ''}}}
        self.all_errors_response_code_map = {}
        # Map of {struct_id: {field_name: header_name}}
        self.all_response_header_map = {}
        # Map of {struct_id: field_name}
        self.all_response_body_map = {}
        self._build(api_provider)

    def _build(self, api_provider):
        """
        Get the metamodel metadata and process it

        :type  api_provider: :class:`vmware.vapi.core.ApiProvider`
        :param api_provider: ApiProvider to get the metadata
        """
        local_connector = get_local_connector(api_provider)
        stub_config = StubConfigurationFactory.new_std_configuration(
            local_connector)
        component_svc = Component(stub_config)
        components = component_svc.list()
        for component_id in components:
            component_data = component_svc.get(component_id)
            self._process_component_info(component_data.info)

    def _process_component_info(self, component_info):
        """
        Process the metamodel component information. Scan the packages
        for services, structures and enumerations and store into dictionaries
        for fast lookup.

        :type  component_info:
               :class:`com.vmware.vapi.metadata.metamodel_client.ComponentInfo`
        :param component_info: Metamodel component information to be processed
        """
        for package_info in six.itervalues(component_info.packages):
            for structure_id, structure_info in six.iteritems(
                                                package_info.structures):
                self._process_structure_info(structure_id, structure_info)
            for enumeration_id, enumeration_info in six.iteritems(
                                                    package_info.enumerations):
                self.enumeration_map[enumeration_id] = enumeration_info
            for service_id, service_info in six.iteritems(
                                            package_info.services):
                self._process_service_info(service_id, service_info)
                self.service_map[service_id] = {
                    operation_id: self._create_operation_summary(operation_info,
                                                                 service_id)
                        for operation_id, operation_info in six.iteritems(
                                                    service_info.operations)}

    def _get_header_and_query_variables(self, param_info_map):
        """
        Get the annotation @Header or @Query parameter alias from metadata.

        :type  param_info_map:
            :class:`collections.OrderedDict` of :class:`str` and
            :class:`com.vmware.vapi.metadata.metamodel_client.FieldInfo`
        :param param_info_map: Map of parameter name to its metamodel metadata
        :rtype: :class: `tuple`
        :return: Tuple containing the @Header and @Query annotation parameter
            alias.
        """
        header_variables = {}
        query_variables = {}
        for param_name, param_info in six.iteritems(param_info_map):
            resource_id = None
            # Get the structure body resource_id from param_info.
            if param_info.type.category == Type.Category.USER_DEFINED:
                resource_id = param_info.type.user_defined_type.resource_id
            # Get the optional structure resource_id from param_info.
            elif param_info.type.category == Type.Category.GENERIC:
                generic_type = param_info.type.generic_instantiation.generic_type  # pylint: disable=line-too-long
                if generic_type == GenericInstantiation.GenericType.OPTIONAL:
                    element_type = param_info.type.generic_instantiation.element_type  # pylint: disable=line-too-long
                    if element_type.category == Type.Category.USER_DEFINED:
                        resource_id = element_type.user_defined_type.resource_id

            # resource_id==None indicates that the parameter is not a struct
            # type and it might be an enum type
            if resource_id is None or resource_id in self.enumeration_map:
                # Get the @Header annotation parameter alias from metadata.
                if RestAnnotations.HEADER_ELEMENT in param_info.metadata:
                    alias = param_info.metadata[
                        RestAnnotations.HEADER_ELEMENT].elements[
                            RestAnnotations.NAME_ELEMENT].string_value
                    header_variables[
                        alias.title().replace('_', '-')] = param_name
                # Get the @Query annotation parameter alias from metadata.
                if RestAnnotations.QUERY_VARIABLE in param_info.metadata:
                    alias = param_info.metadata[
                        RestAnnotations.QUERY_VARIABLE].elements[
                            RestAnnotations.NAME_ELEMENT].string_value
                    query_variables[alias] = param_name
            # resource_id!=None or not in enumerations, indicates that the parameter is of struct type
            else:
                for name, info in six.iteritems(
                                            self.structure_map[resource_id]):
                    if info.type.category != Type.Category.USER_DEFINED:
                        # Get the @Header annotation parameter alias from
                        # the metadata of the structure
                        if RestAnnotations.HEADER_ELEMENT in info.metadata:
                            alias = info.metadata[
                                RestAnnotations.HEADER_ELEMENT].elements[
                                    RestAnnotations.NAME_ELEMENT].string_value
                            name = '%s.%s' % (param_name, name)
                            header_variables[
                                alias.title().replace('_', '-')] = name
                        # Get the @Query annotation parameter alias from
                        # the metadata of the structure
                        if RestAnnotations.QUERY_VARIABLE in info.metadata:
                            alias = info.metadata[
                                RestAnnotations.QUERY_VARIABLE].elements[
                                    RestAnnotations.NAME_ELEMENT].string_value
                            name = '%s.%s' % (param_name, name)
                            query_variables[
                                '%s.%s' % (param_name, alias)] = name

        return header_variables, query_variables

    def _translate_param_name(self, name):
        """
        Changes '__' to '-' in the parameter name. Before registering the
        metadata dashes are changed because werkzeug doesn't allow dashes.

        :type  name: :class:`str`
        :param component_info: parameter name
        :rtype: :class:`str`
        :return: parameter name with dashes instead of '__'
                 If there is nothing to change the provided name is returned
        """
        return name.replace('-', '__')

    def _create_operation_summary(self, operation_info, service_id):
        """
        Generate a summary of the metamodel operation information.

        :type  component_info:
               :class:`com.vmware.vapi.metadata.metamodel_client.OperationInfo`
        :param component_info: Metamodel metadata of an operation
        :rtype: :class:`vmware.vapi.server.rest_handler.MetadataStore.\
            OperationSummary`
        :return: Class containing parameters metadata and annotations in dicts
        """
        param_list = [(param_info.name, param_info)
                      for param_info in operation_info.params]
        param_info_map = collections.OrderedDict(param_list)
        path_variables_map = None
        query_variables_map = None
        header_variables_map = None
        success_response_code = None
        response_headers_map = None
        response_body_name = None
        verb_info = None

        if RestAnnotations.REQUEST_MAPPING in operation_info.metadata.keys():
            # Create a map of value in PathVariable annotation to
            # canonical name of the parameter
            path_variables_map = {
                self._translate_param_name(param_info.metadata[
                    RestAnnotations.PATH_VARIABLE].elements[
                    RestAnnotations.VALUE_ELEMENT].string_value): param_name
                for param_name, param_info in six.iteritems(param_info_map)
                if RestAnnotations.PATH_VARIABLE in param_info.metadata
            }
        elif service_id != 'com.vmware.cis.session':
            if RestAnnotations.VERB_GET in operation_info.metadata.keys():
                verb_info = {RestAnnotations.VERB_GET:
                             operation_info.metadata.get(RestAnnotations.VERB_GET)}  # pylint: disable=line-too-long
            elif RestAnnotations.VERB_POST in operation_info.metadata.keys():
                verb_info = {RestAnnotations.VERB_POST:
                             operation_info.metadata.get(RestAnnotations.VERB_POST)}  # pylint: disable=line-too-long
            elif RestAnnotations.VERB_PUT in operation_info.metadata.keys():
                verb_info = {RestAnnotations.VERB_PUT:
                             operation_info.metadata.get(RestAnnotations.VERB_PUT)}  # pylint: disable=line-too-long
            elif RestAnnotations.VERB_PATCH in operation_info.metadata.keys():
                verb_info = {RestAnnotations.VERB_PATCH:
                             operation_info.metadata.get(
                                 RestAnnotations.VERB_PATCH)}
            elif RestAnnotations.VERB_DELETE in operation_info.metadata.keys():
                verb_info = {RestAnnotations.VERB_DELETE:
                             operation_info.metadata.get(
                                RestAnnotations.VERB_DELETE)}

        if verb_info is not None:
            header_variables_map, query_variables_map = \
                self._get_header_and_query_variables(param_info_map)

            if RestAnnotations.RESPONSE_ELEMENT in operation_info.metadata.keys():  # pylint: disable=line-too-long
                success_response_code = int(operation_info.metadata.get(
                        RestAnnotations.RESPONSE_ELEMENT).elements['code'].string_value)  # pylint: disable=line-too-long

            response_headers_map = {}
            result_type = operation_info.output.type
            # response header can only be annotated within a structure
            # and the structure belongs to user defined category type
            if result_type.category == Type.Category.USER_DEFINED and \
               result_type.user_defined_type.resource_type == \
               Structure.RESOURCE_TYPE:
                structure_name = \
                    result_type.user_defined_type.resource_id
                if structure_name in self.all_response_header_map:
                    header_map = \
                        self.all_response_header_map.get(structure_name)
                    response_headers_map.update(header_map)
                if structure_name in self.all_response_body_map:
                    response_body_name = \
                        self.all_response_body_map.get(structure_name)

        # XXX Instead of long if else above the code should change to line
        # below if metamodel metadata changes to single key
        #verb_info = operation_info.metadata.get(RestAnnotations.REST_DISPATCH)
        return self.OperationSummary(
            param_info_map,
            path_variables_map,
            operation_info.metadata.get(RestAnnotations.REQUEST_MAPPING),
            verb_info,
            query_variables_map,
            header_variables_map,
            success_response_code,
            response_headers_map,
            response_body_name
        )

    def _process_service_info(self, service_id, service_info):
        """
        Process the metamodel service information. Scan the services
        for operations, structures and enumerations and store into dictionaries
        for fast lookup.

        :type  service_id: :class:`str`
        :param service_id: Identifier of the service.
        :type  service_info:
               :class:`com.vmware.vapi.metadata.metamodel_client.ServiceInfo`
        :param service_info: Metamodel service information to be processed
        """
        for structure_id, structure_info in six.iteritems(
                                            service_info.structures):
            self._process_structure_info(structure_id, structure_info)

        for enumeration_id, enumeration_info in six.iteritems(
                                                service_info.enumerations):
            self.enumeration_map[enumeration_id] = enumeration_info

    def _process_structure_info(self, structure_id, structure_info):
        """
        Process the metamodel structure information. Scan the structures for
        for fields and enumerations and store into dictionaries
        for fast lookup.

        :type  structure_id: :class:`str`
        :param structure_id: Identifier of the structure.
        :type  structure_info:
               :class:`com.vmware.vapi.metadata.metamodel_client.StructureInfo`
        :param structure_info: Metamodel structure information to be processed
        """
        field_map = {}
        field_header_map = {}
        for field_info in structure_info.fields:
            field_map[field_info.name] = field_info
            if RestAnnotations.HEADER_ELEMENT in field_info.metadata.keys():
                header_name = field_info.metadata.get(
                    RestAnnotations.HEADER_ELEMENT).elements['name'].string_value  # pylint: disable=line-too-long
                field_header_map[field_info.name] = header_name
            if RestAnnotations.BODY_ELEMENT in field_info.metadata.keys():
                self.all_response_body_map[structure_id] = field_info.name

        self.structure_map[structure_id] = field_map

        if field_header_map:
            self.all_response_header_map[structure_id] = field_header_map

        for enumeration_id, enumeration_info in six.iteritems(
                                                structure_info.enumerations):
            self.enumeration_map[enumeration_id] = enumeration_info

        if structure_info.type == StructureInfo.Type.ERROR \
                and RestAnnotations.RESPONSE_ELEMENT in structure_info.metadata.keys():  # pylint: disable=line-too-long
            error_element = structure_info.metadata.get(RestAnnotations.RESPONSE_ELEMENT)  # pylint: disable=line-too-long
            self.all_errors_response_code_map[structure_id] = \
                int(error_element.elements['code'].string_value)


class URLValueDeserializer(object):
    """
    Deserialize the parameters provided in the HTTP query string
    into a dictionary.

    For example:
        /rest/vmodl/test/uber/rest/filter?
            list_string=string1&
            list_string=string2&
            list_string=string3&
            struct.string_field=string&
            struct.binary_field=aGVsbG8=&
            struct.boolean_field=True&
            struct.long_field=10&
            struct.struct_field.string_field=string&
            struct.struct_field.long_field=10&
            struct.optional_string=string&
            struct.list_string.1=string1&
            struct.list_string.2=string2&
            struct.list_list_long.1.1=11&
            struct.list_list_long.1.2=12&
            struct.list_list_long.2.1=21&
            struct.list_list_long.2.2=22&
            struct.map_simple.1.key=stringkey&
            struct.map_simple.1.value=stringvalue&
            struct.map_struct.1.key=stringkey&
            struct.map_struct.1.value.string_field=string&
            struct.map_struct.1.value.long_field=10

    1. Top level members of the request complex type are referenced by their
       name.
    2. Referencing nested complex structures will use "." and concatenation of
       names.
    3. Whenever arrays of given type are required we will use param.n notation
       to identify the instance number n of the object.

    Deserialized version of this query string will be:
    {
        "list_string": [
            "string1",
            "string2",
            "string3"
        ],
        "struct": {
            "string_field": "string",
            "binary_field": "aGVsbG8=",
            "boolean_field": True,
            "long_field": 10,
            "struct_field": {
                "long_field": 10,
                "string_field": "string"
            },
            "optional_string": "string",
            "list_string": [
                "string1",
                "string2"
            ],
            "list_list_long": [
                [
                    11,
                    12
                ],
                [
                    21,
                    22
                ]
            ],
            "map_simple": [
                {
                    "key": "stringkey",
                    "value": "stringvalue"
                }
            ],
            "map_struct": [
                {
                    "key": "stringkey",
                    "value": {
                        "long_field": 10,
                        "string_field": "string"
                    }
                }
            ]
        }
    }
    """

    @staticmethod
    def deserialize(query_string, mapping_type=RestAnnotationType.VERB):
        """
        Deserialize the given query string into a python dictionary.

        :type  query_string: :class:`str`
        :param query_string: HTTP query string containing parameters.
        :type  mapping_type:
            :class:`vmware.vapi.lib.constants.RestAnnotationType`
        :param mapping_type: Rest annotation type needed for handling map input
        :rtype: :class:`dict` of :class:`str` and :class:`object`
        :return: Python dictionary deserialized from query string.
        """
        # Convert query_string to a key-value pair dictionary
        key_value_pairs = collections.OrderedDict()
        query_string = query_string.decode()
        for item in query_string.split('&'):
            if '=' not in item:
                continue

            pos = item.index('=')
            key = item[:pos]
            value = item[pos + 1:]
            if value != '':
                if key not in key_value_pairs:
                    key_value_pairs[key] = value
                elif isinstance(key_value_pairs[key], six.text_type):
                    key_value_pairs[key] = [key_value_pairs[key], value]
                elif isinstance(key_value_pairs[key], list):
                    key_value_pairs[key].append(value)

        # Deserialize query_string
        query_string_dict = {}
        for k, v in six.iteritems(key_value_pairs):
            tokens = k.split('.')

            # The core idea here is to split the tokens in
            # a.b.c.d type of string and go from left to right.
            # At each step, the next token will be either put
            # at a key in the dictionary or element in a list if
            # the token is a digit.

            # So, at each token, we should look ahead the next token,
            # and if the next token is a digit, then create an empty
            # list or return an existing list where it should be added
            # as element. If the next token is a non-digit, then create
            # a new dictionary or return an existing dictionary where
            # the token should be added as a key.

            current_value = query_string_dict
            key = None
            for i, token in enumerate(tokens):

                # Lookahead the next token
                next_token = None
                if i + 1 < len(tokens):
                    next_token = tokens[i + 1]

                if key is None and mapping_type == RestAnnotationType.VERB:
                    if next_token is None:
                        key = '.'.join(tokens)
                        current_value.setdefault(key, v)
                        current_value = current_value[key]
                        break
                    elif next_token.isdigit():
                        key = '.'.join(tokens[:i + 1])
                        current_value.setdefault(key, [])
                        current_value = current_value[key]
                else:
                    # Next token is the last token
                    if next_token is None:
                        if isinstance(current_value, list):
                            current_value.append(v)  # pylint: disable=E1101
                        elif isinstance(current_value, dict):
                            current_value[token] = v
                    # Next token is not the last token
                    else:
                        # If next token is a digit, create array as placeholder
                        # otherwise a dictionary
                        next_token_type = [] if next_token.isdigit() else {}

                        if isinstance(current_value, list):
                            index = int(token)
                            if index > len(current_value) + 1:
                                msg = (
                                    'Element with index %d is expected, but got'
                                    ' %d' % (len(current_value) + 1, index))
                                logger.error(msg)
                                raise werkzeug.exceptions.BadRequest(msg)
                            elif index == len(current_value) + 1:
                                # pylint: disable=E1101
                                current_value.append(next_token_type)
                            next_value = current_value[index - 1]
                        elif isinstance(current_value, dict):
                            next_value = current_value.setdefault(
                                token, next_token_type)
                        current_value = next_value

        return query_string_dict


class DataValueDeserializer(object):
    """
    Convert from Python dictionary deserialized from a JSON object
    (or) from HTTP URL query string to DataValue.
    """
    _builtin_type_map = {
        Type.BuiltinType.VOID: DataType.VOID,
        Type.BuiltinType.BOOLEAN: DataType.BOOLEAN,
        Type.BuiltinType.LONG: DataType.INTEGER,
        Type.BuiltinType.DOUBLE: DataType.DOUBLE,
        Type.BuiltinType.STRING: DataType.STRING,
        Type.BuiltinType.BINARY: DataType.BLOB,
        Type.BuiltinType.SECRET: DataType.SECRET,
        Type.BuiltinType.DATE_TIME: DataType.STRING,
        Type.BuiltinType.ID: DataType.STRING,
        Type.BuiltinType.URI: DataType.STRING,
        Type.BuiltinType.ANY_ERROR: DataType.ANY_ERROR,
    }
    _builtin_native_type_map = {
        Type.BuiltinType.BOOLEAN: bool,
        Type.BuiltinType.LONG: int,
        Type.BuiltinType.DOUBLE: decimal.Decimal,
        Type.BuiltinType.STRING: six.text_type,
        Type.BuiltinType.BINARY: six.text_type,
        Type.BuiltinType.SECRET: six.text_type,
        Type.BuiltinType.DATE_TIME: six.text_type,
        Type.BuiltinType.ID: six.text_type,
        Type.BuiltinType.URI: six.text_type,
    }

    def __init__(self, metadata):
        """
        Initialize DataValueDeserializer

        :type  metadata: :class:`vmware.vapi.server.rest_handler.MetadataStore`
        :param metadata: Object that contains the metamodel metadata of
            all the services.
        """
        self._metadata = metadata
        self._category_map = {
            Type.Category.BUILTIN: self.visit_builtin,
            Type.Category.USER_DEFINED: self.visit_user_defined,
            Type.Category.GENERIC: self.visit_generic
        }
        self._generic_map = {
            GenericInstantiation.GenericType.OPTIONAL: self.visit_optional,
            GenericInstantiation.GenericType.LIST: self.visit_list,
            GenericInstantiation.GenericType.SET: self.visit_list,
            GenericInstantiation.GenericType.MAP: self.visit_map,
        }

    def get_metadata(self):
        """
        Return the metamodel metadata

        :rtype: :class:`vmware.vapi.server.rest_handler.MetadataStore`
        :return: Metamodel metadata
        """
        return self._metadata

    def visit_builtin(self, type_info, json_value):
        """
        Deserialize a primitive value

        :type  type_info:
            :class:`com.vmware.vapi.metadata.metamodel_client.Type`
        :param type_info: Metamodel type information
        :type  json_value: :class:`object`
        :param json_value: Value to be visited
        :rtype: :class:`vmware.vapi.data.value.DataValue`
        :return: DataValue created using the input
        """
        try:
            builtin_type = type_info.builtin_type
            native_type = self._builtin_native_type_map.get(
                                  builtin_type)
            if native_type == six.text_type:
                if type_info.builtin_type == Type.BuiltinType.BINARY:
                    # For Binary types, we need to convert unicode to bytes
                    base64_encoded_value = json_value.encode()
                    native_value = base64.b64decode(base64_encoded_value)
                else:
                    native_value = json_value
            elif native_type == int:
                native_value = int(json_value)
            elif native_type == decimal.Decimal:
                native_value = decimal.Decimal(json_value)
            elif native_type == bool:
                if isinstance(json_value, bool):
                    native_value = json_value
                elif json_value.lower() == 'true':
                    native_value = True
                elif json_value.lower() == 'false':
                    native_value = False
                else:
                    msg = 'Expected boolean value, but got %s' % json_value
                    logger.error(msg)
                    raise werkzeug.exceptions.BadRequest(msg)
            elif native_type is None:
                if builtin_type == Type.BuiltinType.DYNAMIC_STRUCTURE:
                    return DataValueConverter.convert_to_data_value(
                                                    json.dumps(json_value))
                elif builtin_type == Type.BuiltinType.OPAQUE:
                    if isinstance(json_value, six.text_type):
                        builtin_type = Type.BuiltinType.STRING
                        native_value = json_value
                    elif isinstance(json_value, bool):
                        builtin_type = Type.BuiltinType.BOOLEAN
                        native_value = json_value
                    elif isinstance(json_value, int):
                        builtin_type = Type.BuiltinType.LONG
                        native_value = json_value
                    elif isinstance(json_value, decimal.Decimal):
                        builtin_type = Type.BuiltinType.DOUBLE
                        native_value = decimal.Decimal(json_value)
                    else:
                        msg = ('Expected string or boolean or long or double '
                               'value, but got %s' % json_value)
                        logger.error(msg)
                        raise werkzeug.exceptions.BadRequest(msg)

            data_type = self._builtin_type_map[builtin_type]
            return data_value_factory(data_type, native_value)
        except KeyError:
            msg = ('Could not process the request, '
                   'builtin type %s is not supported' % type_info.builtin_type)
            logger.exception(msg)
            raise werkzeug.exceptions.InternalServerError(msg)

    def visit_user_defined(self, type_info, json_value):
        """
        Deserialize a user defined value

        :type  type_info:
            :class:`com.vmware.vapi.metadata.metamodel_client.Type`
        :param type_info: Metamodel type information
        :type  json_value: :class:`object`
        :param json_value: Value to be visited
        :rtype: :class:`vmware.vapi.data.value.StructValue` or
            :class:`vmware.vapi.data.value.StringValue`
        :return: DataValue created using the input
        """
        user_defined_type_info = type_info.user_defined_type
        if user_defined_type_info.resource_type == Enumeration.RESOURCE_TYPE:
            return StringValue(json_value)
        elif user_defined_type_info.resource_type == Structure.RESOURCE_TYPE:
            structure_info = self._metadata.structure_map[
                user_defined_type_info.resource_id]
            struct_value = StructValue(
                name=user_defined_type_info.resource_id)
            for field_name, field_value in six.iteritems(json_value):
                try:
                    field_info = structure_info[str(field_name)]
                    field_data_value = self.visit(field_info.type, field_value)
                    struct_value.set_field(field_name, field_data_value)
                except KeyError:
                    msg = 'Unexpected field \'%s\' in request' % field_name
                    logger.error(msg)
                    raise werkzeug.exceptions.BadRequest(msg)
            return struct_value
        else:
            msg = ('Could not process the request,'
                   'user defined type %s is not supported' %
                   user_defined_type_info.resource_type)
            logger.error(msg)
            raise werkzeug.exceptions.InternalServerError(msg)

    def visit_optional(self, type_info, json_value):
        """
        Deserialize an optional value

        :type  type_info:
            :class:`com.vmware.vapi.metadata.metamodel_client.Type`
        :param type_info: Metamodel type information
        :type  json_value: :class:`object`
        :param json_value: Value to be visited
        :rtype: :class:`vmware.vapi.data.value.OptionalValue`
        :return: DataValue created using the input
        """
        if json_value is not None:
            element_value = self.visit(type_info.element_type, json_value)
            return OptionalValue(element_value)
        else:
            return OptionalValue()

    def visit_list(self, type_info, json_value):
        """
        Deserialize a list value

        :type  type_info:
            :class:`com.vmware.vapi.metadata.metamodel_client.Type`
        :param type_info: Metamodel type information
        :type  json_value: :class:`object`
        :param json_value: Value to be visited
        :rtype: :class:`vmware.vapi.data.value.ListValue`
        :return: DataValue created using the input
        """
        if not isinstance(json_value, list):
            msg = 'Excepted list, but got %s' % type(json_value).__name__
            logger.error(msg)
            raise werkzeug.exceptions.BadRequest(msg)
        return ListValue([
            self.visit(type_info.element_type, value) for value in json_value])

    def visit_map(self, type_info, json_value):
        """
        Deserialize a map value

        :type  type_info:
            :class:`com.vmware.vapi.metadata.metamodel_client.Type`
        :param type_info: Metamodel type information
        :type  json_value: :class:`object`
        :param json_value: Value to be visited
        :rtype: :class:`vmware.vapi.data.value.StructValue`
        :return: DataValue created using the input
        """
        # For new Rest annotations map deserializes to StructValue instead of
        # ListValue for old annotations
        if (self.mapping_type == RestAnnotationType.VERB):
            if not isinstance(json_value, dict):
                msg = 'Excepted dict, but got %s' % type(json_value).__name__
                logger.error(msg)
                raise werkzeug.exceptions.BadRequest(msg)

            struct_value = StructValue()
            for field_name, field_value in six.iteritems(json_value):
                try:
                    field_data_value = self.visit(type_info.map_value_type,
                                                  field_value)
                    struct_value.set_field(field_name, field_data_value)
                except KeyError:
                    msg = 'Unexpected field \'%s\' in request' % field_name
                    logger.error(msg)
                    raise werkzeug.exceptions.BadRequest(msg)
            return struct_value
        else:
            if not isinstance(json_value, list):
                msg = 'Excepted list, but got %s' % type(json_value).__name__
                logger.error(msg)
                raise werkzeug.exceptions.BadRequest(msg)
            try:
                return ListValue(
                    [StructValue(
                        name=MAP_ENTRY,
                        values={
                            'key': self.visit(
                                type_info.map_key_type, value['key']),
                            'value': self.visit(
                                type_info.map_value_type, value['value'])
                        })
                        for value in json_value])
            except KeyError as e:
                msg = 'Invalid Map input, missing %s' % e
                logger.error(msg)
                raise werkzeug.exceptions.BadRequest(msg)

    def visit_generic(self, type_info, json_value):
        """
        Deserialize a list/optional/map value

        :type  type_info:
            :class:`com.vmware.vapi.metadata.metamodel_client.Type`
        :param type_info: Metamodel type information
        :type  json_value: :class:`object`
        :param json_value: Value to be visited
        :rtype: :class:`vmware.vapi.data.value.OptionalValue` or
            :class:`vmware.vapi.data.value.ListValue` or
            :class:`vmware.vapi.data.value.StructValue`
        :return: DataValue created using the input
        """
        try:
            generic_type_info = type_info.generic_instantiation
            generic_convert_method = \
                self._generic_map[generic_type_info.generic_type]
            return generic_convert_method(generic_type_info, json_value)
        except KeyError:
            msg = ('Could not process the request, generic type '
                   '%s is not supported' % generic_type_info.generic_type)
            logger.exception(msg)
            raise werkzeug.exceptions.InternalServerError(msg)

    def visit(self, type_info, json_value):
        """
        Deserialize the given input using the metamodel type information

        :type  type_info:
            :class:`com.vmware.vapi.metadata.metamodel_client.Type`
        :param type_info: Metamodel type information
        :type  json_value: :class:`object`
        :param json_value: Value to be visited
        :rtype: :class:`vmware.vapi.data.value.DataValue`
        :return: DataValue created using the input
        """
        convert_method = self._category_map[type_info.category]
        return convert_method(type_info, json_value)

    def generate_operation_input(self, service_id, operation_id, input_data,
                                 mapping_type):
        """
        This method generates a StructValue corresponding to the Python dict
        (deserialized from JSON) suitable as an input value for the specified
        operation.

        :type  service_id: :class:`str`
        :param service_id: Identifier of the service to be invoked.
        :type  operation_id: :class:`str`
        :param operation_id: Identifier of the operation to be invoked.
        :type  input_data: :class:`dict`
        :param input_data: Dictionary object that represents the deserialized
            json input.
        :type  mapping_type:
            :class:`vmware.vapi.lib.constants.RestAnnotationType`
        :param mapping_type: Rest annotation type needed for handling map input
        :rtype: :class:`vmware.vapi.data.value.DataValue` or
        :return: DataValue created using the input
        """

        param_info_map = \
            self._metadata.service_map[service_id][operation_id].param_info_map

        self.mapping_type = mapping_type
        try:
            fields = {
                param_name: self.visit(param_info_map[str(param_name)].type,
                                       param_value)
                for param_name, param_value in six.iteritems(input_data)}
        except KeyError as e:
            msg = 'Unexpected parameter %s in JSON body' % e
            logger.exception(msg)
            raise werkzeug.exceptions.BadRequest(msg)
        except CoreException as e:
            msg = 'Unexpected input in JSON body: %s' % e
            logger.exception(msg)
            raise werkzeug.exceptions.BadRequest(msg)
        return StructValue(name=OPERATION_INPUT, values=fields)

    def map_uri_params(self, uri_parameters, service_id, operation_id):
        """
        If RequestMapping annotation is present, map URI parameters to
        respective parameter names. When request mapping is provided, it is
        possible that the uri parameter name is different from the canonical
        name of the parameter.

        :type  uri_parameters: :class:`dict` of :class:`str` and :class:`object`
        :param uri_parameters: Arguments parsed from the HTTP URL
        :type  service_id: :class:`str`
        :param service_id: Identifier of the service to be invoked
        :type  operation_id: :class:`str`
        :param operation_id: Identifier of the operation to be invoked
        :rtype: :class:`dict` of :class:`str` and :class:`object`
        :return: Arguments parsed from the HTTP URL - path_variable name
                 replaced with the canonical name of the parameter
        """
        service = self._metadata.service_map[service_id]
        operation = service[operation_id]

        if not operation.has_request_mapping_metadata():
            return uri_parameters

        path_variables_map = operation.path_variables_map

        # Update keys in uri_parameters from path variable name to canonical
        # name of the parameter
        return {path_variables_map[name]: value
                for name, value in six.iteritems(uri_parameters)}

    def _change_parameter_structure(self, output, names, value):
        """
        Multilevel parameter names are converted to dictionaries and the
        corresponding parameter values are set..

        For example, suppose the input parameter values are as follows:
            output = {'spec': 'index': 5}
            names = ['spec', 'body', 'user']
            value = 'Bob'

        Returns the result:
            {
                'spec': {
                    'index': 5,
                    'body': {
                        'user': 'Bob'
                    }
                }
            }

        :type  output: :class:`dict`
        :param output: Converted parameter dictionary.
        :type  names: :class: :`list`
        :param names: Multilevel parameter name list.
        :type  value: :class: :`string` or `list` or `dict`.
        :param value: Parameter value.
        :rtype: :class:`dict`
        :return: Parameter dictionary.
        """
        param_dict = dict(output)
        name = names.pop(0)
        if len(names) > 0:
            sub_param_dict = {}
            if name in output and isinstance(output[name], dict):
                sub_param_dict = output[name]
            param_dict[name] = self._change_parameter_structure(
                                    sub_param_dict, names, value)
        else:
            param_dict[name] = value
        return param_dict

    def map_query_params(self, request, service_id, operation_id):
        """
        For Verb annotation map Query parameters to respective parameter names.

        :type  service_id: :class:`str`
        :param service_id: Identifier of the service to be invoked
        :type  operation_id: :class:`str`
        :param operation_id: Identifier of the operation to be invoked
        :rtype: :class:`dict` of :class:`str` and :class:`object`
        :return: Query variables - canonical name of the parameter
        """
        service = self._metadata.service_map[service_id]
        operation = service[operation_id]

        if not operation.has_verb_metadata:
            return None

        output_data = {}
        for key, value in six.iteritems(
                        URLValueDeserializer.deserialize(request.query_string)):
            if key != TASK_REST_QUERY_PARAM and \
                                    key in operation.query_variables_map:
                output_data = self._change_parameter_structure(
                    output=output_data,
                    names=operation.query_variables_map[key].split('.'),
                    value=value
                )
        return output_data

    def map_header_params(self, request, service_id, operation_id):
        """
        For Verb annotation map Header parameters to respective parameter names.

        :type  service_id: :class:`str`
        :param service_id: Identifier of the service to be invoked
        :type  operation_id: :class:`str`
        :param operation_id: Identifier of the operation to be invoked
        :rtype: :class:`dict` of :class:`str` and :class:`object`
        :return: Header variables - canonical name of the parameter
        """
        service = self._metadata.service_map[service_id]
        operation = service[operation_id]

        if not operation.has_verb_metadata:
            return None

        output_data = {}
        for key, value in six.iteritems(request.headers):
            if key in operation.header_variables_map:
                output_data = self._change_parameter_structure(
                    output=output_data,
                    names=operation.header_variables_map[key].split('.'),
                    value=value
                )
        return output_data


class SecurityContextBuilder(object):
    """
    Helper class to build the appropriate security context based
    on the authentication information present in the request context.
    """
    def __init__(self, parsers):
        """
        Initialize SecurityContextBuilder

        :type  parsers: :class:`list` of :class:`str`
        :param parsers: List of names of Security Parsers
        """
        #
        # The order in the variable determines the order in which
        # the security parsers parse the request. The first parser
        # that can create a security context is used.
        #
        # If the request contains more than one kind of security
        # related information, the first one that gets parsed is used.
        # And if that information is invalid, 401 UNAUTHORIZED
        # is returned to the client. The other security information
        # that is not parsed is not taken into consideration.
        #
        # The user has to remove the invalid security context and invoke
        # the operation again.
        #
        self._parsers = [parser_class()
                         for parser_class in dynamic_import_list(parsers)]

    def build(self, request):
        """
        Build the security context based on the authentication information
        in the request context

        :type  request: :class:`werkzeug.wrappers.Request`
        :param request: Request object
        :rtype: :class:`vmware.vapi.core.SecurityContext`
        :return: Security context
        """
        for parser in self._parsers:
            security_context = parser.build(request)
            if security_context:
                return security_context
        return None


class ResponseCookieBuilder(object):
    """
    Helper class to build the appropriate cookies to be set
    in the response.
    """
    def __init__(self, session_methods):
        """
        Initialize ResponseCookieBuilder

        :type  session_methods: :class:`list` of :class:`str`
        :param session_methods: List of names of session login methods
        """
        self._session_methods = session_methods

    def build(self, service_id, operation_id, method_result):
        """
        Build the response cookie for the request

        :type  service_id: :class:`str`
        :param service_id: Identifier of the service to be invoked.
        :type  operation_id: :class:`str`
        :param operation_id: Identifier of the operation to be invoked.
        :type  method_result: :class:`vmware.vapi.core.MethodResult`
        :param method_result: MethodResult object to be serialized
        :rtype: :class:`dict` of :class:`str` and :class:`str`
        :return: Dictionary containing cookies that need to be set in the
            response.
        """
        session_method = '%s.%s' % (service_id, operation_id)
        if session_method in self._session_methods:
            if isinstance(method_result.output, (StringValue, SecretValue)):
                session_id = method_result.output.value
            return {REST_SESSION_ID_KEY: session_id}
        return None


class ApplicationContextBuilder(object):
    """
    Helper class to build the appropriate application context.
    """

    def build(self, request):
        """
        Build the application context based on the HTTP request. It will look
        for the header via which opID can be passed and put it into
        ApplicationContext or create the default one otherwise.

        :type  request: :class:`werkzeug.wrappers.Request`
        :param request: Request object
        :rtype: :class:`vmware.vapi.core.ApplicationContext`
        :return: Application context
        """
        headers = {}
        op_id = request.headers.get(REST_OP_ID_HEADER)
        if op_id:
            headers[OPID] = op_id

        locale = request.headers.get(HTTP_ACCEPT_LANGUAGE)
        if locale:
            headers[LOCALE] = locale

        locale_format = request.headers.get(HTTP_FORMAT_LOCALE)
        if locale_format:
            headers[HTTP_FORMAT_LOCALE] = locale_format

        timezone = request.headers.get(HTTP_TIMEZONE)
        if timezone:
            headers[HTTP_TIMEZONE] = timezone

        if headers:
            return ApplicationContext(headers)
        else:
            return create_default_application_context()


class RESTHandler(object):
    """
    Request handler that accept REST API calls and invoke the corresponding
    call on ApiProvider interface.
    """
    def __init__(self, api_provider, allow_cookies=True, provider_config=None):
        """
        Initialize RESTHandler

        :type  api_provider: :class:`vmware.vapi.core.ApiProvider`
        :param api_provider: ApiProvider to be used to invoke the vAPI requests
        :type  allow_cookies: :class:`bool`
        :param allow_cookies: Whether cookie support should be enabled
        :type  provider_config:
            :class:`vmware.vapi.settings.config.ProviderConfig` or :class:`None`
        :param provider_config: ApiProvider to be used to invoke the vAPI
            requests
        """
        self._api_provider = api_provider
        self.metadata = MetadataStore(api_provider)
        self.rest_rules = RoutingRuleGenerator(
            self.metadata, provider_config.get_rest_prefix()).rest_rules
        self.data_value_deserializer = DataValueDeserializer(self.metadata)
        self.application_context_builder = ApplicationContextBuilder()
        self.security_context_builder = SecurityContextBuilder(
            provider_config.get_rest_security_parsers())
        self.response_cookie_builder = ResponseCookieBuilder(
            provider_config.get_rest_session_methods()) \
            if allow_cookies else None

    def _get_input_value(self, service_id, operation_id, input_data,
                         mapping_type):
        """
        Generate the input DataValue for the given operation

        :type  service_id: :class:`str`
        :param service_id: Identifier of the service to be invoked.
        :type  operation_id: :class:`str`
        :param operation_id: Identifier of the operation to be invoked.
        :type  input_data: :class:`dict`
        :param input_data: Dictionary object that represents the deserialized
            json input.
        :type  mapping_type:
            :class:`vmware.vapi.lib.constants.RestAnnotationType`
        :param mapping_type: Rest annotation type needed for handling map input
        """
        try:
            return self.data_value_deserializer.generate_operation_input(
                service_id, operation_id, input_data, mapping_type)
        except werkzeug.exceptions.BadRequest as e:
            raise e
        except Exception as e:
            msg = 'Cannot process request: %s' % e
            logger.exception(msg)
            raise werkzeug.exceptions.InternalServerError(msg)

    def _serialize_output(
            self, request, service_id, operation_id, method_result,
            use_cookies, mapping_type):
        """
        Serialize the MethodResult object

        :type  request: :class:`werkzeug.wrappers.Request`
        :param request: Request object
        :type  service_id: :class:`str`
        :param service_id: Identifier of the service to be invoked.
        :type  operation_id: :class:`str`
        :param operation_id: Identifier of the operation to be invoked.
        :type  method_result: :class:`vmware.vapi.core.MethodResult`
        :param method_result: MethodResult object to be serialized
        :type  use_cookies: :class:`bool`
        :param use_cookies: Whether cookies are to be sent in response
        :rtype: :class:`tuple` of :class:`int`, :class:`str`, :class:`dict`
        :return: HTTP status code, serialized json output of the operation,
            a dictionary of response cookies and response http headers
        """
        status = None
        http_headers = None

        operation_summary = self.metadata.service_map[service_id][operation_id]
        response_headers = operation_summary.response_headers_map
        response_body_name = operation_summary.response_body_name

        if method_result.success():
            if self.response_cookie_builder is None or not use_cookies:
                cookies = None
            else:
                cookies = self.response_cookie_builder.build(
                    service_id, operation_id, method_result)
            output = method_result.output
            json_output = None
            if not isinstance(output, VoidValue):
                if not isinstance(output, StructValue):
                    # If the output is not a struct or error value,
                    # box it with {'value':..} to make it a
                    # good json output
                    output = StructValue(name='output', values={
                        'value': output
                    })

                new_rest = mapping_type == RestAnnotationType.VERB
                json_output = DataValueConverter.convert_to_json(output,
                                                                 new_rest)

            if operation_summary.success_response_code is not None:
                status = operation_summary.success_response_code
            else:
                status = 200
            if request.method == 'DELETE':
                status = 204
        else:
            error_name = method_result.error.name
            if error_name in self.metadata.all_errors_response_code_map:
                status = self.metadata.all_errors_response_code_map[error_name]

            cookies = None
            error = method_result.error
            new_rest = mapping_type == RestAnnotationType.VERB
            json_output = DataValueConverter.convert_to_json(error,
                                                             new_rest)
            if status is None:
                status = vapi_to_http_error_map.get(error.name, 500)

        if json_output:
            json_output_obj = json.loads(json_output)
            if response_headers:
                http_headers = {response_headers[key]: json_output_obj[key]
                                for key in json_output_obj.keys()
                                if key in response_headers}

            response_body = json.loads(json_output)
            if response_body_name:
                # if there is @Body annotation, the result can only contain
                # that field, nothing else.
                if response_body_name in response_body.keys():
                    json_output = json.dumps(response_body[response_body_name])
                else:
                    json_output = ''
            elif response_headers:
                for key in json_output_obj.keys():
                    if key in response_headers.keys():
                        del response_body[key]
                json_output = json.dumps(response_body)

        return (status, json_output, cookies, http_headers)

    def _find_matching_operation(
            self,
            request,
            service_id,
            uri_parameters,
            query_string_flat_dict,
            dispatch_info_list):
        """
        Find matching operation

        :type  request: :class:`werkzeug.wrappers.Request`
        :param request: Request object
        :type  service_id: :class:`str`
        :param service_id: Identifier of the service to be invoked.
        :type  uri_parameters: :class:`dict` of :class:`str` and :class:`object`
        :param uri_parameters: Arguments parsed from the HTTP URL
        :type  query_string_flat_dict: :class:`dict` of :class:`str` and :class:`object`  # pylint: disable=line-too-long
        :param query_string_flat_dict: Arguments parsed from the HTTP URL
        :type  dispatch_info_list:  :class:`list` of :class:`DispatchInfo`
        :param dispatch_info_list: List of dispatch info object
        :rtype: :class:`tuple` of :class:`str`, :class:`str`, :class:`dict`
        :return: Operation id, annotation type and response code map
        """

        operation_id = None
        mapping_type = RestAnnotationType.NONE
        arity = 0

        # If there's just one dispatch target get that operation id.
        if len(dispatch_info_list) == 1 and \
                dispatch_info_list[0].mapping_type != RestAnnotationType.VERB:
            operation_id = dispatch_info_list[0].operation_id
            mapping_type = dispatch_info_list[0].mapping_type
        else:
            for dispatch_info in dispatch_info_list:
                curr_op_id, curr_arity, curr_type = \
                    dispatch_info.get_operation_id(
                        request, query_string_flat_dict, uri_parameters)

                if curr_op_id is not None and curr_arity >= arity:
                    operation_id = curr_op_id
                    arity = curr_arity
                    mapping_type = curr_type

            if operation_id is None:
                action = query_string_flat_dict.get(
                    RestAnnotations.ACTION_PARAM)
                if action is not None:
                    msg = 'No matching method available for the requested ' + \
                        'action \'%s\' on the URL' % action
                else:
                    msg = 'No matching method available for the requested ' + \
                        'URL and HTTP method'
                logger.error(msg)
                raise werkzeug.exceptions.NotFound(msg)

        # Check if it's a task invocation
        is_task = query_string_flat_dict.get(TASK_REST_QUERY_PARAM)
        if is_task is not None:
            if is_task.lower() == 'true':
                operation_id = get_task_operation_name(operation_id)
            else:
                msg = 'Invalid value for "%s" query param' % (
                            TASK_REST_QUERY_PARAM)
                logger.error(msg)
                raise werkzeug.exceptions.BadRequest(msg)

        if operation_id not in self.data_value_deserializer.get_metadata().service_map[service_id]:  # pylint: disable=line-too-long
            msg = 'No matching method available for the requested ' + \
                  'URL and HTTP method'
            logger.error(msg)
            raise werkzeug.exceptions.NotFound(msg)

        return (operation_id, mapping_type)

    def _input_data_update(self, input_data, update_data):
        """
        The dictionary to merge.

        For example, if you have two dictionaries
        {
            'header_string': 'first',
            'query_bool': True,
            'spec': {
                'query_long': 1
            }
        }
        and
        {
            'body_double': 1.0,
            'spec': {
                'body_list': [2, 3, 4]
            }
        }
        the combined result
        output_data = {
            'header_string': 'first',
            'query_bool': True,
            'body_double': 1.0,
            'spec': {
                'query_long': 1,
                'body_list': [2, 3, 4]
            }
        }

        :type  input_data: :class:`dict`
        :param input_data: HTTP passes in the parameter dictionary.
        :type  update_data: :class:`dict`
        :param update_data: The parameter dictionary to be appended.
        :rtype :class:`dict`
        :return The updated HTTP passes in the parameter dictionary.
        """
        tmp = dict(input_data)
        for key, value in six.iteritems(update_data):
            if key in tmp and isinstance(tmp[key], dict) and \
                    isinstance(value, dict):
                tmp[key] = self._input_data_update(tmp[key], value)
            else:
                tmp.update({key: value})
        return tmp

    def invoke(self, request, endpoint, uri_parameters):
        """
        Handle the REST API invocation

        :type  request: :class:`werkzeug.wrappers.Request`
        :param request: Request object
        :type  endpoint: :class:`tuple` of :class:`tuple` of :class:`str` and
        :class:`str`
        :param endpoint: Tuple of service ID and dispatch_info is a tuples of
        tuples of (action, operation_id)
        :type  uri_parameters: :class:`dict` of :class:`str` and :class:`object`
        :param uri_parameters: Arguments parsed from the HTTP URL
        :rtype: :class:`tuple` of :class:`int`, :class:`str`, :class:`dict`
        :return: HTTP status code, serialized json output of the operation,
            response cookies and http headers
        """

        # Operation input is contributed by:
        # 1. URI parameters: Arguments parsed from HTTP URL
        # 2. Query parameters: Arguments parsed from the query string in the
        #               HTTP URL
        # 3. Header parameters: Arguments parsed from HTTP Header
        # 4. Request body: Arguments present in request body
        #
        # There is a definitive place for each argument, a particular argument
        # can be passed only using one of the above ways.
        #
        # Typically, main object identifiers are present in the base HTTP URL.
        # For GET operations, additional parameters can be provided in the query
        # string. For POST, PUT, PATCH, parameters can only be provided using
        # the body

        query_string_flat_dict = werkzeug.urls.url_decode(
            request.query_string)
        (service_id, dispatch_info_list) = endpoint
        (operation_id, mapping_type) = \
            self._find_matching_operation(request,
                                          service_id,
                                          uri_parameters,
                                          query_string_flat_dict,
                                          dispatch_info_list)

        input_data = self.data_value_deserializer.map_uri_params(
            uri_parameters, service_id, operation_id)

        if mapping_type == RestAnnotationType.VERB:
            input_data = self._input_data_update(
                input_data, self.data_value_deserializer.map_query_params(
                    request, service_id, operation_id))

            input_data = self._input_data_update(
                input_data, self.data_value_deserializer.map_header_params(
                    request, service_id, operation_id))

        if request.method == 'GET' and mapping_type != RestAnnotationType.VERB:
            query_string_parameters = URLValueDeserializer.deserialize(
                request.query_string, mapping_type)
            # Currently we put all query params for GET requests in request
            # body, don't do that for TASK_REST_QUERY_PARAM
            input_data = self._input_data_update(
                input_data, {
                    key: query_string_parameters[key]
                        for key in query_string_parameters
                            if key != TASK_REST_QUERY_PARAM})

        if request.method in ['PUT', 'PATCH', 'POST']:
            request_body_string = request.get_data()
            if request_body_string:
                try:
                    if isinstance(request_body_string, six.string_types):
                        input_data = self._input_data_update(
                            input_data, json.loads(
                                request_body_string,
                                parse_float=decimal.Decimal))
                    elif isinstance(request_body_string, six.binary_type):
                        input_data = self._input_data_update(
                            input_data, json.loads(
                                request_body_string.decode('utf-8'),
                                parse_float=decimal.Decimal))
                except ValueError as e:
                    msg = 'Invalid JSON in request body: %s' % e
                    logger.error(msg)
                    raise werkzeug.exceptions.BadRequest(msg)

        # Create request context
        security_context = self.security_context_builder.build(request)
        application_context = self.application_context_builder.build(request)
        ctx = ExecutionContext(
            application_context=application_context,
            security_context=security_context)

        # Set application context for the current operation/thread
        set_context(ctx)

        input_value = self._get_input_value(
            service_id, operation_id, input_data, mapping_type)

        method_result = self._api_provider.invoke(
            service_id, operation_id, input_value, ctx)

        # Clear application context from the current operation/thread
        clear_context()

        use_cookies = REQUIRE_HEADER_AUTHN not in request.headers
        return self._serialize_output(
            request, service_id, operation_id,
            method_result, use_cookies, mapping_type)
