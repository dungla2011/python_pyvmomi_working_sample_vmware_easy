# -*- coding: utf-8 -*-

"""
Type converter to/from vAPI runtime data model to Python native data model
"""
__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015-2019 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import base64
import six

from vmware.vapi.bindings.type import (
    BindingTypeVisitor, OptionalType, IntegerType, MAP_KEY_FIELD,
    MAP_VALUE_FIELD)
from vmware.vapi.bindings.enum import Enum
from vmware.vapi.bindings.error import (VapiError, UnresolvedError)
from vmware.vapi.bindings.struct import VapiStruct
from vmware.vapi.bindings.datetime_helper import DateTimeConverter
from vmware.vapi.bindings.uri_helper import URIValidator
from vmware.vapi.data.serializers.python import build_data_value
from vmware.vapi.exception import CoreException
from vmware.vapi.lib.constants import MAP_STRUCT
from vmware.vapi.lib.converter import Converter
from vmware.vapi.lib.log import get_vapi_logger
from vmware.vapi.data.value import DataValue, OptionalValue, StructValue
from vmware.vapi.l10n.runtime import message_factory

logger = get_vapi_logger(__name__)


class RestConverter(object):
    """
    Constants for different REST converter modes
    """
    VAPI_REST = 'VAPI_REST'
    SWAGGER_REST = 'SWAGGER_REST'


class PythonToVapiJsonRpcDataValueVisitor(BindingTypeVisitor):
    """
    Visitor to convert from Python native value to vAPI JSON-RPC compatible
    DataValue
    """
    def __init__(self, value):
        """
        Initialize PythonToVapiJsonRpcDataValueVisitor

        :type  value: :class:`object`
        :param value: Native python value
        """
        self._in_value = value
        self._out_value = None
        BindingTypeVisitor.__init__(self)

    def get_out_value(self):
        """
        Returns the vAPI DataValue converted from the Python native value

        :rtype: :class:`vmware.vapi.data.value.DataValue`
        :return: vAPI DataValue
        """
        return self._out_value

    def visit_primitive(self, typ):
        """
        Visit a primitive type python value

        :type  typ: :class:`vmware.vapi.bindings.type.BindingType`
        :param typ: Binding type of the value
        """
        self._out_value = typ.definition.new_value(self._in_value)

    def visit_void(self, typ):
        """
        Visit a void value (i.e. None)

        :type  typ: :class:`vmware.vapi.bindings.type.VoidType`
        :param typ: Binding type of the value
        """
        if self._in_value is not None:
            msg = message_factory.get_message(
                'vapi.bindings.typeconverter.voiddef.expect.null',
                type(self._in_value).__name__)
            logger.debug(msg)
            raise CoreException(msg)
        self._out_value = typ.definition.new_value()

    def visit_integer(self, typ):
        """
        Visit an integer value

        :type  typ: :class:`vmware.vapi.bindings.type.IntegerType`
        :param typ: Binding type of the value
        """
        self.visit_primitive(typ)

    def visit_double(self, typ):
        """
        Visit an double value

        :type  typ: :class:`vmware.vapi.bindings.type.DoubleType`
        :param typ: Binding type of the value
        """
        self.visit_primitive(typ)

    def visit_string(self, typ):
        """
        Visit an string value

        :type  typ: :class:`vmware.vapi.bindings.type.StringType`
        :param typ: Binding type of the value
        """
        self.visit_primitive(typ)

    def visit_secret(self, typ):
        """
        Visit an secret value

        :type  typ: :class:`vmware.vapi.bindings.type.SecretType`
        :param typ: Binding type of the value
        """
        self.visit_primitive(typ)

    def visit_boolean(self, typ):
        """
        Visit an boolean value

        :type  typ: :class:`vmware.vapi.bindings.type.BooleanType`
        :param typ: Binding type of the value
        """
        self.visit_primitive(typ)

    def visit_id(self, typ):
        """
        Visit an id value

        :type  typ: :class:`vmware.vapi.bindings.type.IdType`
        :param typ: Binding type of the value
        """
        self.visit_primitive(typ)

    def visit_blob(self, typ):
        """
        Visit an blob value

        :type  typ: :class:`vmware.vapi.bindings.type.BlobType`
        :param typ: Binding type of the value
        """
        self.visit_primitive(typ)

    def visit_opaque(self, typ):
        """
        Visit an opaque value. Don't do any conversion.

        :type  typ: :class:`vmware.vapi.bindings.type.OpaqueType`
        :param typ: Binding type of the value
        """
        if not isinstance(self._in_value, DataValue):
            msg = message_factory.get_message(
                'vapi.bindings.typeconverter.unexpected.python.type',
                 DataValue.__name__, type(self._in_value).__name__)
            logger.debug(msg)
            raise CoreException(msg)
        self._out_value = self._in_value

    def visit_list(self, typ):
        """
        Visit a list value

        :type  typ: :class:`vmware.vapi.bindings.type.ListType`
        :param typ: Binding type of the value
        """
        in_value = self._in_value
        out_value = typ.definition.new_value()
        elt_typ = typ.element_type
        for elt_value in in_value:
            self._in_value = elt_value
            self.visit(elt_typ)
            out_value.add(self._out_value)
        self._in_value = in_value
        self._out_value = out_value

    def visit_set(self, typ):
        """
        Visit a python set

        :type  typ: :class:`vmware.vapi.bindings.type.SetType`
        :param typ: Binding type of the value
        """
        if not isinstance(self._in_value, (set, frozenset)):
            msg = message_factory.get_message(
                'vapi.bindings.typeconverter.invalid',
                'set', type(self._in_value))
            logger.debug(msg)
            raise CoreException(msg)
        self.visit_list(typ)

    def visit_map(self, typ):
        """
        Visit a python dict

        :type  typ: :class:`vmware.vapi.bindings.type.MapType`
        :param typ: Binding type of the value
        """
        in_value = self._in_value
        out_value = typ.definition.new_value()
        out_value.set_map(True)
        struct_def = typ.definition.element_type
        for k, v in six.iteritems(in_value):
            struct_val = struct_def.new_value()
            self._in_value = k
            self.visit(typ.key_type)
            struct_val.set_field(MAP_KEY_FIELD, self._out_value)
            self._in_value = v
            self.visit(typ.value_type)
            struct_val.set_field(MAP_VALUE_FIELD, self._out_value)
            out_value.add(struct_val)
        self._in_value = in_value
        self._out_value = out_value

    def _visit_vapi_struct(self, typ):
        """
        Visit an instance of VapiStruct class

        :type  typ: :class:`vmware.vapi.bindings.type.StructType`
        :param typ: Binding type of the value
        :rtype: :class:`vmware.vapi.data.value.DataValue`
        :return: vAPI Data value
        """
        # Check if it is the expected struct class
        expected_name = typ.name
        actual_name = self._in_value.get_binding_type().name
        # TODO: compare the types instead of names.
        if expected_name != actual_name:
            msg = message_factory.get_message(
                'vapi.bindings.typeconverter.unexpected.struct.class',
                expected_name, actual_name)
            logger.debug(msg)
            raise CoreException(msg)
        in_value = self._in_value
        out_value = typ.definition.new_value()
        field_names = typ.get_field_names()
        for field in field_names:
            try:
                self._in_value = in_value.get_field(field)
                # If self._in_value is None and field type is not
                # optional, raise an error
                field_type = typ.get_field(field)
                if (not isinstance(field_type, OptionalType)
                        and self._in_value is None):
                    raise AttributeError
            except AttributeError:
                msg = message_factory.get_message(
                    'vapi.bindings.typeconverter.struct.missing.field',
                    field, typ.name)
                logger.debug(msg)
                raise CoreException(msg)

            try:
                self.visit(typ.get_field(field))
            except Exception as e:
                msg = message_factory.get_message(
                    'vapi.bindings.typeconverter.struct.invalid.field',
                    field, typ.name)
                logger.debug(msg)
                raise CoreException(msg, e)
            out_value.set_field(field, self._out_value)

        for k, v in six.iteritems(in_value._get_extra_fields()):  # pylint: disable=W0212
            out_value.set_field(k, v)
        self._in_value = in_value
        self._out_value = out_value

    def _visit_python_dict(self, typ):
        """
        Visit an instance of Python native dictionary

        :type  typ: :class:`vmware.vapi.bindings.type.StructType`
        :param typ: Binding type of the value
        :rtype: :class:`vmware.vapi.data.value.DataValue`
        :return: vAPI Data value
        """
        in_value = self._in_value
        out_value = typ.definition.new_value()
        field_names = typ.get_field_names()
        for field_name in field_names:
            field_type = typ.get_field(field_name)
            try:
                if typ.binding_class:
                    # pylint: disable=W0212
                    pep_name = typ.binding_class._get_pep_name(field_name)
                else:
                    pep_name = Converter.canonical_to_pep(field_name)
                self._in_value = in_value[pep_name]
            except KeyError:
                if isinstance(field_type, OptionalType):
                    # If the field is optional, then tolerate
                    # the absence of it in the dictionary
                    self._in_value = None
                else:
                    msg = message_factory.get_message(
                        'vapi.bindings.typeconverter.dict.missing.key',
                        pep_name)
                    logger.debug(msg)
                    raise CoreException(msg)
            self.visit(field_type)
            out_value.set_field(field_name, self._out_value)
        self._in_value = in_value
        self._out_value = out_value

    def visit_struct(self, typ):
        """
        Visit a struct value

        :type  typ: :class:`vmware.vapi.bindings.type.StructType`
        :param typ: Binding type of the value
        """
        if isinstance(self._in_value, VapiStruct):
            self._visit_vapi_struct(typ)
            # Validating the constraints in the struct value
            # before sending it over the wire. The validation does
            # not happen during initialization of VapiStruct or
            # StructValue
            self._in_value.validate_struct_value(self._out_value)

        elif isinstance(self._in_value, dict):
            self._visit_python_dict(typ)
        else:
            msg = message_factory.get_message(
                'vapi.bindings.typeconverter.unexpected.struct.type',
                type(self._in_value).__name__)
            logger.debug(msg)
            raise CoreException(msg)

    def visit_error(self, typ):
        """
        Visit an error value

        :type  typ: :class:`vmware.vapi.bindings.type.ErrorType`
        :param typ: Binding type of the value
        """
        if isinstance(self._in_value, VapiError):
            self._visit_vapi_struct(typ)
        else:
            msg = message_factory.get_message(
                'vapi.bindings.typeconverter.unexpected.error.type',
                type(self._in_value).__name__)
            logger.debug(msg)
            raise CoreException(msg)

    def visit_dynamic_struct(self, typ):
        """
        Visit any struct value

        :type  typ: :class:`vmware.vapi.bindings.type.DynamicStructType`
        :param typ: Binding type of the value
        """
        if self._in_value.__class__.__name__ == 'VapiStruct':
            self._out_value = self._in_value.get_struct_value()
        elif self._in_value.__class__.__name__ == 'VapiError':
            self._out_value = self._in_value.get_error_value()
        elif isinstance(self._in_value, VapiStruct):
            self._visit_vapi_struct(self._in_value.get_binding_type())
        elif isinstance(self._in_value, StructValue):
            self._out_value = self._in_value
        elif isinstance(self._in_value, dict):
            self._out_value = build_data_value(self._in_value, typ.definition)
        else:
            msg = message_factory.get_message(
                'vapi.bindings.typeconverter.unexpected.python.type',
                 StructValue.__name__, type(self._in_value).__name__)
            logger.debug(msg)
            raise CoreException(msg)

    def visit_any_error(self, typ):
        """
        Visit any error value

        :type  typ: :class:`vmware.vapi.bindings.type.AnyErrorType`
        :param typ: Binding type of the value
        """
        if isinstance(self._in_value, UnresolvedError):
            self._out_value = self._in_value.get_error_value()
        elif isinstance(self._in_value, VapiError):
            self._visit_vapi_struct(self._in_value.get_binding_type())
        else:

            msg = message_factory.get_message(
                'vapi.bindings.typeconverter.unexpected.python.type',
                 VapiError.__name__, type(self._in_value).__name__)
            logger.debug(msg)
            raise CoreException(msg)

    def visit_optional(self, typ):
        """
        Visit an optional value

        :type  typ: :class:`vmware.vapi.bindings.type.OptionalType`
        :param typ: Binding type of the value
        """
        if self._in_value is None:
            self._out_value = typ.definition.new_value()
        else:
            self.visit(typ.element_type)
            self._out_value = typ.definition.new_value(self._out_value)

    def visit_date_time(self, typ):
        """
        Visit a datetime value

        :type  typ: :class:`vmware.vapi.bindings.type.DateTimeType`
        :param typ: Binding type of the value
        """
        dt_str = DateTimeConverter.convert_from_datetime(self._in_value)
        self._out_value = typ.definition.new_value(dt_str)

    def visit_uri(self, typ):
        """
        Visit an URI value

        :type  typ: :class:`vmware.vapi.bindings.type.UriType`
        :param typ: Binding type of the value
        """
        URIValidator.validate(self._in_value)
        self._out_value = typ.definition.new_value(self._in_value)

    def visit_reference(self, typ):
        """
        Visit a reference type

        :type  typ: :class:`vmware.vapi.bindings.type.ReferenceType`
        :param typ: Binding type of the value
        """
        self.visit(typ.resolved_type)

    def visit_enum(self, typ):
        """
        Visit a enum type python value

        :type  typ: :class:`vmware.vapi.bindings.type.EnumType`
        :param typ: Binding type of the value
        """
        # If the binding type is EnumType, we will accept either
        # a plain string (or) a class variable of
        # :class:`vmware.vapi.bindings.enum.Enum` type.
        # String will be sent when the user invoked an API call
        # by sending a plain dictionary object (deserialized
        # from a human readable JSON).
        # Enum will be sent when the user use a language binding type
        # to invoke an operation.
        if not isinstance(self._in_value, six.string_types):
            msg = message_factory.get_message(
                'vapi.bindings.typeconverter.unexpected.python.type',
                typ.name, type(self._in_value).__name__)
            logger.debug(msg)
            raise CoreException(msg)
        if isinstance(self._in_value, Enum):
            # Check if it is the expected enum class
            expected_name = typ.name
            actual_name = self._in_value.get_binding_type().name
            # TODO: compare the types instead of names.
            if expected_name != actual_name:
                msg = message_factory.get_message(
                    'vapi.bindings.typeconverter.unexpected.enum.type',
                    expected_name, actual_name)
                logger.debug(msg)
                raise CoreException(msg)
        # Convert from vmware.vapi.bindings.Enum instance to string value
        enum_string_value = str(self._in_value)
        self._out_value = typ.definition.new_value(enum_string_value)


class VapiJsonRpcDataValueToPythonVisitor(BindingTypeVisitor):
    """
    Visitor to convert from vAPI JSON-RPC compatible DataValue to Python native
    value
    """
    def __init__(self, value, resolver):
        """
        Initialize VapiJsonRpcDataValueToPythonVisitor

        :type  value: :class:`vmware.vapi.data.value.DataValue`
        :param value: vAPI DataValue to be converted
        :type  resolver: :class:`vmware.vapi.bindings.common.NameToTypeResolver`
            or ``None``
        :param resolver: Type resolver
        """
        self._in_value = value
        self._resolver = resolver
        self._out_value = None
        self._allow_skip_struct_fields = False
        BindingTypeVisitor.__init__(self)

    def get_out_value(self):
        """
        Returns the Python native value converted from the vAPI DataValue

        :rtype: :class:`object`
        :return: Native python value
        """
        return self._out_value

    def visit_primitive(self, typ):  # pylint: disable=W0613
        """
        Visit one of the primitive DataValues

        :type  typ: :class:`vmware.vapi.bindings.type.BindingType`
        :param typ: Binding type of the value
        """
        self._out_value = self._in_value.value

    def visit_void(self, typ):
        """
        Since VoidValue does not have any value, just return None

        :type  typ: :class:`vmware.vapi.bindings.type.VoidType`
        :param typ: Binding type of the value
        """
        self._out_value = None

    def visit_string(self, typ):
        """
        Visit StringValue

        :type  typ: :class:`vmware.vapi.bindings.type.StringType`
        :param typ: Binding type of the value
        """
        try:
            self._out_value = str(self._in_value.value)
        except UnicodeError:
            self._out_value = self._in_value.value

    def visit_integer(self, typ):
        """
        Visit IntegerValue

        :type  typ: :class:`vmware.vapi.bindings.type.IntegerType`
        :param typ: Binding type of the value
        """
        self.visit_primitive(typ)

    def visit_id(self, typ):
        """
        Visit IdValue

        :type  typ: :class:`vmware.vapi.bindings.type.IdType`
        :param typ: Binding type of the value
        """
        self.visit_primitive(typ)

    def visit_boolean(self, typ):
        """
        Visit BooleanValue

        :type  typ: :class:`vmware.vapi.bindings.type.BooleanType`
        :param typ: Binding type of the value
        """
        self.visit_primitive(typ)

    def visit_double(self, typ):
        """
        Visit DoubleValue

        :type  typ: :class:`vmware.vapi.bindings.type.DoubleType`
        :param typ: Binding type of the value
        """
        self.visit_primitive(typ)

    def visit_secret(self, typ):
        """
        Visit SecretValue

        :type  typ: :class:`vmware.vapi.bindings.type.SecretType`
        :param typ: Binding type of the value
        """
        self.visit_primitive(typ)

    def visit_blob(self, typ):
        """
        Visit BlobValue

        :type  typ: :class:`vmware.vapi.bindings.type.BlobType`
        :param typ: Binding type of the value
        """
        self.visit_primitive(typ)

    def visit_opaque(self, typ):
        """
        Since there is no OpaqueValue, don't do any conversion

        :type  typ: :class:`vmware.vapi.bindings.type.OpaqueType`
        :param typ: Binding type of the value
        """
        self._out_value = self._in_value

    def _visit_list_element(self, value, typ):
        """
        Visit a ListValue element

        :type  value: :class:`vmware.vapi.data.value.DataValue`
        :param value: element value
        :type  typ: :class:`vmware.vapi.bindings.type.ListType`
        :param typ: Binding type of the element
        """
        self._in_value = value
        self.visit(typ)
        return self._out_value

    def visit_list(self, typ):
        """
        Visit a ListValue

        :type  typ: :class:`vmware.vapi.bindings.type.ListType`
        :param typ: Binding type of the value
        """
        elt_typ = typ.element_type
        in_value = self._in_value
        self._out_value = [self._visit_list_element(elt_value, elt_typ)
                           for elt_value in in_value]
        self._in_value = in_value

    def visit_set(self, typ):
        """
        Visit a List Value. This ListValue must represent a set
        i.e. there must not be any duplicate elements

        :type  typ: :class:`vmware.vapi.bindings.type.SetType`
        :param typ: Binding type of the value
        """
        elt_typ = typ.element_type
        in_value = self._in_value
        out_value = set()
        for elt_value in in_value:
            elt = self._visit_list_element(elt_value, elt_typ)
            if elt in out_value:
                msg = message_factory.get_message(
                    'vapi.bindings.typeconverter.set.duplicate.element',
                    elt)
                logger.debug(msg)
                raise CoreException(msg)
            out_value.add(elt)
        self._out_value = out_value
        self._in_value = in_value

    def visit_map(self, typ):
        """
        Visit a List Value. This ListValue must represent a map. Each element
        of the ListValue is a StructValue with two fields, namely 'key' and
        'value'. The 'key' field represents the key of the map and the 'value'
        field represents the value of the map. Also, since this represents a
        map, there should not be duplicate keys.

        :type  typ: :class:`vmware.vapi.bindings.type.MapType`
        :param typ: Binding type of the value
        """
        in_value = self._in_value
        key_typ = typ.key_type
        value_typ = typ.value_type
        out_value = {}

        # For REST 2018 maps
        if isinstance(in_value, StructValue):
            for k, v in in_value.get_fields():
                if isinstance(key_typ, IntegerType):
                    key_value = int(k)
                else:
                    key_value = k
                self._in_value = v
                self.visit(value_typ)
                out_value[key_value] = self._out_value
        else:
            for elt_value in in_value:
                key = self._visit_struct_field(
                    elt_value.get_field(MAP_KEY_FIELD), key_typ)
                if key in out_value:
                    msg = message_factory.get_message(
                        'vapi.bindings.typeconverter.map.duplicate.key',
                        key)
                    logger.debug(msg)
                    raise CoreException(msg)
                value = self._visit_struct_field(
                    elt_value.get_field(MAP_VALUE_FIELD), value_typ)
                out_value[key] = value
        self._out_value = out_value
        self._in_value = in_value

    def _visit_struct_field(self, value, typ):
        """
        Visit a field of a StructValue

        :type  value: :class:`vmware.vapi.data.value.DataValue`
        :param value: field value
        :type  typ: :class:`vmware.vapi.bindings.type.StructType`
        :param typ: Binding type of the struct field
        """
        self._in_value = value
        self.visit(typ)
        return self._out_value

    def visit_struct(self, typ):
        """
        Visit StructValue

        :type  typ: :class:`vmware.vapi.bindings.type.StructType`
        :param typ: Binding type of the value
        """
        in_value = self._in_value
        out_value = {}
        typ_field_names = typ.get_field_names()
        value_field_names = in_value.get_field_names()

        for field_name in typ_field_names:
            if typ.binding_class:
                pep_name = typ.binding_class._get_pep_name(field_name)  # pylint: disable=W0212
            else:
                pep_name = Converter.canonical_to_pep(field_name)
            field_type = typ.get_field(field_name)
            # When the request is converted from DataValue to Native value
            # on the server side:
            # - if the client - server version matches: we wont hit this case
            # - if new client talks to old server, runtime would have
            #   raised InvalidArgument error if there are unexpected optional
            #   fields
            # - if old client talks to new server, runtime adds the missing
            #   optional fields, so we wont hit this case
            #
            # When the response is converted from DataValue to Native value
            # on the client side:
            # - if the client - server version matches: we wont hit this case
            # - if new client talks to old server,  client bindings should
            #   tolerate the absence of expected optional properties. So,
            #   we have to set it to None!
            # - if old client talks to new server, we will visit all the known
            #   fields here and the unexpected fields are added to the
            #   VapiStruct object
            if ((isinstance(field_type, OptionalType) or self._allow_skip_struct_fields)
                    and not in_value.has_field(field_name)):
                out_value[pep_name] = None
            else:
                out_value[pep_name] = self._visit_struct_field(
                    in_value.get_field(field_name), field_type)
        self._in_value = in_value

        struct_class = typ.binding_class
        if struct_class is not None:
            struct_class.validate_struct_value(self._in_value)
            self._out_value = struct_class(**out_value)

            # Fields present in struct value but not in struct binding type.
            extra_field_names = set(value_field_names) - set(typ_field_names)
            if extra_field_names:
                extra_fields = {}
                for field_name in extra_field_names:
                    extra_fields[field_name] = in_value.get_field(field_name)
                self._out_value._set_extra_fields(extra_fields)  # pylint: disable=E1103,W0212
        else:
            self._out_value = out_value

    def visit_dynamic_struct(self, typ):
        """
        Visit StructValue to convert it into the base VapiStruct

        :type  typ: :class:`vmware.vapi.bindings.type.DynamicStructType`
        :param typ: Binding type of the value
        """
        self._out_value = VapiStruct(struct_value=self._in_value)

    def visit_any_error(self, typ):
        """
        Visit ErrorValue to convert it into the base VapiError

        :type  typ: :class:`vmware.vapi.bindings.type.AnyErrorType`
        :param typ: Binding type of the value
        """
        typ = self._resolver and self._resolver.resolve(self._in_value.name)
        if typ is None:
            self._out_value = UnresolvedError(self._in_value)
        else:
            typ.accept(self)

    def visit_error(self, typ):
        """
        Visit ErrorValue

        :type  typ: :class:`vmware.vapi.bindings.type.ErrorType`
        :param typ: Binding type of the value
        """
        self.visit_struct(typ)

    def visit_optional(self, typ):
        """
        Visit OptionalValue

        :type  typ: :class:`vmware.vapi.bindings.type.OptionalType`
        :param typ: Binding type of the value
        """
        if isinstance(self._in_value, OptionalValue):
            if self._in_value.is_set():
                self._in_value = self._in_value.value
                self.visit(typ.element_type)
            else:
                self._out_value = None
        else:
            # Invalid data value
            msg = message_factory.get_message(
                'vapi.bindings.typeconverter.invalid',
                OptionalValue.__name__, type(self._in_value).__name__)
            logger.debug(msg)
            raise CoreException(msg)

    def visit_date_time(self, typ):
        """
        Visit a datetime value

        :type  typ: :class:`vmware.vapi.bindings.type.DateTimeType`
        :param typ: Binding type of the value
        """
        self._out_value = DateTimeConverter.convert_to_datetime(
            self._in_value.value)

    def visit_uri(self, typ):
        """
        Visit an URI value

        :type  typ: :class:`vmware.vapi.bindings.type.UriType`
        :param typ: Binding type of the value
        """
        uri_string = self._in_value.value
        URIValidator.validate(uri_string)
        self._out_value = uri_string

    def visit_enum(self, typ):
        """
        Visit an Enum value

        :type  typ: :class:`vmware.vapi.bindings.type.EnumType`
        :param typ: Binding type of the value
        """
        enum_string = self._in_value.value
        if typ.binding_class:
            try:
                self._out_value = getattr(typ.binding_class, enum_string)
            except AttributeError:
                self._out_value = typ.binding_class(enum_string)
        else:
            self._out_value = Enum(enum_string)

    def visit_reference(self, typ):
        """
        Visit a reference type

        :type  typ: :class:`vmware.vapi.bindings.type.ReferenceType`
        :param typ: Binding type of the value
        """
        self.visit(typ.resolved_type)


class PythonToVapiRestDataValueVisitor(PythonToVapiJsonRpcDataValueVisitor):
    """
    Visitor to convert from Python native value to vAPI REST compatible
    DataValue
    """
    def __init__(self, value):
        """
        Initialize PythonToVapiJsonRpcDataValueVisitor

        :type  value: :class:`object`
        :param value: Native python value
        """
        PythonToVapiJsonRpcDataValueVisitor.__init__(self, value)


class VapiRestDataValueToPythonVisitor(VapiJsonRpcDataValueToPythonVisitor):
    """
    Visitor to convert from vAPI REST compatible DataValue to Python native
    value
    """
    def __init__(self, value, resolver):
        """
        Initialize VapiJsonRpcDataValueToPythonVisitor

        :type  value: :class:`vmware.vapi.data.value.DataValue`
        :param value: vAPI DataValue to be converted
        :type  resolver: :class:`vmware.vapi.bindings.common.NameToTypeResolver`
            or ``None``
        :param resolver: Type resolver
        """
        VapiJsonRpcDataValueToPythonVisitor.__init__(self, value, resolver)

    def visit_optional(self, typ):
        """
        Visit OptionalValue

        :type  typ: :class:`vmware.vapi.bindings.type.OptionalType`
        :param typ: Binding type of the value
        """
        if isinstance(self._in_value, OptionalValue):
            if self._in_value.is_set():
                self._in_value = self._in_value.value
                self.visit(typ.element_type)
            else:
                self._out_value = None
        else:
            # OptionalValue wrapper is missing
            self.visit(typ.element_type)

    def visit_dynamic_struct(self, typ):
        """
        Visit StructValue to convert it into the base VapiStruct

        :type  typ: :class:`vmware.vapi.bindings.type.DynamicStructType`
        :param typ: Binding type of the value
        """
        self._out_value = VapiStruct(
            struct_value=self._in_value,
            rest_converter_mode=RestConverter.VAPI_REST)

    def visit_blob(self, typ):
        """
        Visit BlobValue

        :type  typ: :class:`vmware.vapi.bindings.type.BlobType`
        :param typ: Binding type of the value
        """
        # Byte string will be base64 encoded and then 'utf-8' decoded to a
        # unicode string
        unicode_str = self._in_value.value
        bytes_str = base64.b64decode(unicode_str.encode())
        self._out_value = bytes_str


class PythonToSwaggerRestDataValueVisitor(PythonToVapiJsonRpcDataValueVisitor):
    """
    Visitor to convert from Python native value to Swagger Rest compatible
    DataValue
    """
    def __init__(self, value):
        """
        Initialize PythonToVapiJsonRpcDataValueVisitor

        :type  value: :class:`object`
        :param value: Native python value
        """
        PythonToVapiJsonRpcDataValueVisitor.__init__(self, value)

    def visit_map(self, typ):
        """
        Visit a python dict

        :type  typ: :class:`vmware.vapi.bindings.type.MapType`
        :param typ: Binding type of the value
        """
        in_value = self._in_value
        out_value = StructValue(MAP_STRUCT)
        for k, v in six.iteritems(in_value):
            self._in_value = k
            self.visit(typ.key_type)
            key_value = self._out_value.value
            self._in_value = v
            self.visit(typ.value_type)
            out_value.set_field(key_value, self._out_value)
        self._in_value = in_value
        self._out_value = out_value


class SwaggerRestDataValueToPythonVisitor(VapiJsonRpcDataValueToPythonVisitor):
    """
    Visitor to convert from Swagger Rest compatible DataValue to Python native
    value
    """
    def __init__(self, value, resolver):
        """
        Initialize VapiJsonRpcDataValueToPythonVisitor

        :type  value: :class:`vmware.vapi.data.value.DataValue`
        :param value: vAPI DataValue to be converted
        :type  resolver: :class:`vmware.vapi.bindings.common.NameToTypeResolver`
            or ``None``
        :param resolver: Type resolver
        """
        VapiJsonRpcDataValueToPythonVisitor.__init__(self, value, resolver)

    def visit_optional(self, typ):
        """
        Visit OptionalValue

        :type  typ: :class:`vmware.vapi.bindings.type.OptionalType`
        :param typ: Binding type of the value
        """
        if isinstance(self._in_value, OptionalValue):
            if self._in_value.is_set():
                self._in_value = self._in_value.value
                self.visit(typ.element_type)
            else:
                self._out_value = None
        else:
            # OptionalValue wrapper is missing
            self.visit(typ.element_type)

    def visit_map(self, typ):
        """
        Visit a StructValue. This ListValue must represent a map. Each element
        of the ListValue is a StructValue with two fields, namely 'key' and
        'value'. The 'key' field represents the key of the map and the 'value'
        field represents the value of the map. Also, since this represents a
        map, there should not be duplicate keys.

        :type  typ: :class:`vmware.vapi.bindings.type.MapType`
        :param typ: Binding type of the value
        """
        in_value = self._in_value
        value_typ = typ.value_type
        out_value = {}
        for key, field_value in in_value.get_fields():
            if key in out_value:
                msg = message_factory.get_message(
                    'vapi.bindings.typeconverter.map.duplicate.key',
                    key)
                logger.debug(msg)
                raise CoreException(msg)
            value = self._visit_struct_field(field_value, value_typ)
            out_value[key] = value
        self._out_value = out_value
        self._in_value = in_value

    def visit_dynamic_struct(self, typ):
        """
        Visit StructValue to convert it into the base VapiStruct

        :type  typ: :class:`vmware.vapi.bindings.type.DynamicStructType`
        :param typ: Binding type of the value
        """
        self._out_value = VapiStruct(
            struct_value=self._in_value,
            rest_converter_mode=RestConverter.SWAGGER_REST)

    def visit_blob(self, typ):
        """
        Visit BlobValue

        :type  typ: :class:`vmware.vapi.bindings.type.BlobType`
        :param typ: Binding type of the value
        """
        # Byte string will be base64 encoded and then 'utf-8' decoded to a
        # unicode string
        unicode_str = self._in_value.value
        bytes_str = base64.b64decode(unicode_str.encode())
        self._out_value = bytes_str

    def visit_date_time(self, typ):
        """
        Visit a datetime value

        :type  typ: :class:`vmware.vapi.bindings.type.DateTimeType`
        :param typ: Binding type of the value
        """
        self._out_value = DateTimeConverter.convert_from_rfc3339_to_datetime(
            self._in_value.value)

class TypeConverter(object):
    """
    Converter class that converts values from vAPI data model to Python native
    data model
    """

    @staticmethod
    def convert_to_python(vapi_val, binding_type, resolver=None,
                          rest_converter_mode=None):
        """
        Converts vAPI DataValue to Python native value

        :type  vapi_val: :class:`vmware.vapi.data.value.DataValue`
        :param vapi_val: vAPI DataValue to be converted
        :type  binding_type: :class:`vmware.vapi.bindings.type.BindingType`
        :param binding_type: BindingType for the value
        :type  resolver: :class:`vmware.vapi.bindings.common.NameToTypeResolver`
            or ``None``
        :param resolver: Type resolver
        :type  rest_converter_mode: :class:`str` or :class:`None`
        :param rest_converter_mode: Converter mode to be used to be be
            compatible for Vapi Rest. If None or unknown string value, then the
            default Json Rpc converter is used
        :rtype: :class:`object`
        :return: Python native value
        """
        if rest_converter_mode == RestConverter.VAPI_REST:
            visitor = VapiRestDataValueToPythonVisitor(vapi_val, resolver)
        elif rest_converter_mode == RestConverter.SWAGGER_REST:
            visitor = SwaggerRestDataValueToPythonVisitor(vapi_val, resolver)
        else:
            visitor = VapiJsonRpcDataValueToPythonVisitor(vapi_val, resolver)
        binding_type.accept(visitor)
        return visitor.get_out_value()

    @staticmethod
    def convert_to_vapi(py_val, binding_type, rest_converter_mode=None):
        """
        Converts Python native value to vAPI DataValue

        :type  py_val: :class:`object`
        :param py_val: Python native value to be converted
        :type  binding_type: :class:`vmware.vapi.bindings.type.BindingType`
        :param binding_type: BindingType for the value
        :type  rest_converter_mode: :class:`str` or :class:`None`
        :param rest_converter_mode: Converter mode to be used to be be
            compatible for Vapi Rest. If None or unknown string value, then the
            default Json Rpc converter is used
        :rtype: :class:`vmware.vapi.data.value.DataValue`
        :return: vAPI DataValue
        """
        if rest_converter_mode == RestConverter.VAPI_REST:
            visitor = PythonToVapiRestDataValueVisitor(py_val)
        elif rest_converter_mode == RestConverter.SWAGGER_REST:
            visitor = PythonToSwaggerRestDataValueVisitor(py_val)
        else:
            visitor = PythonToVapiJsonRpcDataValueVisitor(py_val)
        binding_type.accept(visitor)
        return visitor.get_out_value()
