"""
Representation of an IDL type for the use of the Python language bindings.
"""
__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import six

from vmware.vapi.data.definition import (
    IntegerDefinition, DoubleDefinition, BooleanDefinition, StringDefinition,
    BlobDefinition, VoidDefinition, OpaqueDefinition, ListDefinition,
    StructDefinition, OptionalDefinition, SecretDefinition, StructRefDefinition,
    ErrorDefinition, ReferenceResolver, DynamicStructDefinition,
    AnyErrorDefinition)
from vmware.vapi.lib.constants import MAP_ENTRY
from vmware.vapi.lib.load import dynamic_import
from vmware.vapi.lib.visitor import VapiVisitor

MAP_KEY_FIELD = 'key'
MAP_VALUE_FIELD = 'value'


class BindingType(object):
    """
    Representation of an IDL type for the use of the Python language bindings

    :type  definition: :class:`vmware.vapi.data.definition.DataDefinition`
    :param definition: Data definition corresponding to this binding type
    """
    def __init__(self):
        self._definition = None

    def accept(self, visitor):
        """
        Applies a visitor to this BindingType

        :type  visitor: :class:`BindingTypeVisitor`
        :param visitor: visitor operating on the BindingType
        """
        visitor.visit(self)

    @property
    def definition(self):
        """
        Generate the data defintion corresponding to this binding type
        """
        # This will make sure that we only generate the definition once
        # for every instance of binding type
        if self._definition is None:
            self._definition = TypeUtil.convert_to_data_definition(self)
        return self._definition


class VoidType(BindingType):
    """
    Representation of void IDL type in Python Binding
    """
    def __init__(self):
        BindingType.__init__(self)


class IntegerType(BindingType):
    """
    Representation of integer IDL Type in Python Binding
    """
    def __init__(self):
        BindingType.__init__(self)


class DoubleType(BindingType):
    """
    Representation of float IDL Type in Python Binding
    """
    def __init__(self):
        BindingType.__init__(self)


class StringType(BindingType):
    """
    Representation of string IDL Type in Python Binding
    """
    def __init__(self):
        BindingType.__init__(self)


class SecretType(BindingType):
    """
    Representation of @secret IDL annotation in Python Binding. @secret
    annotation can only be applied to strings.
    """
    def __init__(self):
        BindingType.__init__(self)


class BooleanType(BindingType):
    """
    Representation of boolean IDL Type in Python Binding
    """
    def __init__(self):
        BindingType.__init__(self)


class BlobType(BindingType):
    """
    Representation of binary IDL Type in Python Binding
    """
    def __init__(self):
        BindingType.__init__(self)


class OptionalType(BindingType):
    """
    Representation of optional IDL annotation in Python Binding

    :type element_type: :class:`BindingType`
    :ivar element_type: element type
    """
    def __init__(self, element_type):
        if not isinstance(element_type, BindingType):
            raise TypeError(
                'Expected an instance of BindingType as element_type parameter '
                + 'of OptionalType() but got %s' % type(element_type).__name__)
        self._element_type = element_type
        BindingType.__init__(self)

    @property
    def element_type(self):
        """
        Return the element type of this ListType

        :rtype: :class:`BindingType`
        :return: element type
        """
        return self._element_type


class ListType(BindingType):
    """
    Representation of List IDL type in Python Binding

    :type element_type: :class:`BindingType`
    :ivar element_type: element type
    """
    def __init__(self, element_type):
        if not isinstance(element_type, BindingType):
            raise TypeError(
                'Expected an instance of BindingType as element_type parameter '
                + 'of ListType() but got %s' % type(element_type).__name__)
        self._element_type = element_type
        BindingType.__init__(self)

    @property
    def element_type(self):
        """
        Return the element type of this ListType

        :rtype: :class:`BindingType`
        :return: element type
        """
        return self._element_type


class SetType(BindingType):
    """
    Representation of Set IDL type in Python Binding

    :type element_type: :class:`BindingType`
    :ivar element_type: element type
    """
    def __init__(self, element_type):
        if not isinstance(element_type, BindingType):
            raise TypeError(
                'Expected an instance of BindingType as element_type parameter '
                + 'of SetType() but got %s' % type(element_type).__name__)
        self._element_type = element_type
        BindingType.__init__(self)

    @property
    def element_type(self):
        """
        Return the element type of this SetType

        :rtype: :class:`BindingType`
        :return: element type
        """
        return self._element_type


class MapType(BindingType):
    """
    Representation of Map IDL type in Python Binding

    :type key_type: :class:`BindingType`
    :ivar key_type: map key type
    :type value_type: :class:`BindingType`
    :ivar value_type: map value type
    """
    def __init__(self, key_type, value_type):
        if (not isinstance(key_type, BindingType)
                or not isinstance(value_type, BindingType)):
            raise TypeError(
                'Expected an instance of BindingType for both key_type and '
                'value_type parameters of MapType() but got '
                '%s and %s respectively'
                % (type(key_type).__name__, type(value_type).__name__))
        self._key_type = key_type
        self._value_type = value_type
        BindingType.__init__(self)

    @property
    def key_type(self):
        """
        Return the key type of this MapType

        :rtype: :class:`BindingType`
        :return: key type
        """
        return self._key_type

    @property
    def value_type(self):
        """
        Return the value type of this MapType

        :rtype: :class:`BindingType`
        :return: value type
        """
        return self._value_type


class StructType(BindingType):
    """
    Representation of Structure IDL type in Python Binding

    :type name: :class:`str`
    :ivar name: Name of the structure
    :type binding_class: :class:`vmware.vapi.bindings.struct.VapiStruct`
    :ivar binding_class: Reference to the Python native class corresponding
                         to this structure
    :type is_model: :class:`bool`
    :ivar is_model: True if the structure is marked as Model, False otherwise
    :type model_keys: :class:`list` of :class:`str` or :class:`None`
    :ivar model_keys: List of model keys for the structure if it is marked as
        Model
    """
    def __init__(self, name, fields, binding_class=None, is_model=False,
                 model_keys=None):
        if not isinstance(name, six.string_types):
            raise TypeError('Structure name must be a string')
        if not isinstance(fields, dict):
            raise TypeError('Structure fields must be a dict')
        for field_name, binding_type in six.iteritems(fields):
            if not isinstance(binding_type, BindingType):
                raise TypeError(
                    'Type of the field %s in StructType should be a BindingType'
                    ' but got %s for one of the fields'
                    % (field_name, type(binding_type).__name__))
        self._name = name
        self._binding_class = binding_class
        self._field_map = fields
        self._is_model = is_model
        self._model_keys = model_keys
        BindingType.__init__(self)

    @property
    def name(self):
        """
        Returns the name of the StructType

        :rtype: :class:`str`
        :return: Name of the StructType
        """
        return self._name

    @property
    def binding_class(self):
        """
        Returns the reference to the Python native class
        corresponding to this structure

        :rtype: :class:`vmware.vapi.bindings.struct.VapiStruct`
        :return: Reference to the python native class
        """
        return self._binding_class

    @property
    def is_model(self):
        """
        Check if the Struct is marked as model

        :rtype: :class:`bool`
        :return: True if the Struct is marked as model, False otherwise
        """
        return self._is_model

    @property
    def model_keys(self):
        """
        Returns list of model keys for the Struct if it is marked as model

        :rtype: :class:`list` of :class:`str` or None
        :return: List of model keys for the Struct if it is marked as model
        """
        return self._model_keys

    def get_field_names(self):
        """
        Returns the list of field names present in this StructType

        :rtype: :class:`list` of :class:`str`
        :return: List of field names
        """
        return list(self._field_map.keys())

    def get_field(self, field_name):
        """
        Returns the BindingType of the argument

        :type  field_name: :class:`str`
        :param field_name: Field name
        :rtype: :class:`BindingType`
        :return: BindingType of the field specified
        """
        return self._field_map.get(field_name)


class ErrorType(StructType):
    """
    Representation of Error IDL type in Python Binding

    :type definition: :class:`vmware.vapi.data.ErrorDefinition`
    :ivar definition: type representation in the API runtime
    :type name: :class:`str`
    :ivar name: Name of the structure
    :type binding_class: :class:`vmware.vapi.bindings.error.VapiError`
    :ivar binding_class: Reference to the Python native class corresponding
                         to this error
    """
    def __init__(self, name, fields, binding_class=None):
        StructType.__init__(self, name, fields, binding_class)


class ReferenceType(BindingType):
    """
    Reference type to resolve references lazily.

    :type resolved_type: :class:`StructType` or :class:`EnumType`
    :ivar resolved_type: Resolved reference type
    """
    def __init__(self, context_name, type_name):
        """
        Initialize ReferenceType

        :type  context_name: :class:`str`
        :param context_name: Name of the module that has the type
        :type  type_name: :class:`str`
        :param type_name: Fully qualified name of the type reference. i.e.
            if the type Bar is nested inside type Foo, it would be Foo.Bar
        """
        if not isinstance(type_name, six.string_types):
            raise TypeError('Type name should be a string')
        self._type_name = type_name
        if not isinstance(context_name, six.string_types):
            raise TypeError('Context name should be a string')
        self._context_name = context_name
        self._resolved_type = None
        BindingType.__init__(self)

    def _resolve(self):
        """
        Resolves the struct or enum reference
        """
        tokens = self._type_name.split('.')
        target = dynamic_import(self._context_name)
        # Get the required reference by walking down the fully qualified name
        for token in tokens:
            target = getattr(target, token)
        self._resolved_type = target.get_binding_type()

    @property
    def resolved_type(self):
        """
        Returns the resolved struct type or enum type

        :rtype: :class:`StructType` or
            :class:`EnumType`
        :return: Resolved struct type or enum type
        """
        if self._resolved_type is None:
            self._resolve()
        return self._resolved_type


class OpaqueType(BindingType):
    """
    Representation of Opaque IDL annotation in Python Binding
    """
    def __init__(self):
        BindingType.__init__(self)


class DynamicStructType(StructType):
    """
    Representation of StructValue IDL annotation in Python Binding

    :type has_fields_of_type: :class:`ReferenceType`
    :ivar has_fields_of_type: List of reference types whose fields need to be
        present in the StructValue for this DynamicStruct type
    """
    def __init__(self, name, fields, binding_class=None,
                 has_fields_of_type=None):
        """
        Initialize DynamicStructType

        :type  name: :class:`str`
        :param name: Name of the Structure
        :type  fields: :class:`dict` of :class:`str` and :class:`BindingType`
        :param fields: Map of field name and field binding type
        :type  binding_class:
            :class:`vmware.vapi.data.definition.DataDefinition`
        :param binding_class: Data definition for this type
        :type  has_fields_of_type: :class:`ReferenceType`
        :param has_fields_of_type: List of reference types whose fields need to
            be present in the StructValue for this DynamicStruct type
        """
        StructType.__init__(self, name, fields, binding_class)
        self._has_fields_of_type = has_fields_of_type

    @property
    def has_fields_of_type(self):
        """
        Returns the has_fields_of_type

        :rtype  :class:`ReferenceType`
        :return List of reference types whose fields need to be present in the
            StructValue for this DynamicStruct type
        """
        return self._has_fields_of_type


class AnyErrorType(BindingType):
    """
    Representation of Exception type in Python Binding
    """
    def __init__(self):
        """
        Initialize AnyErrorType
        """
        BindingType.__init__(self)


class DateTimeType(BindingType):
    """
    Representation of datetime IDL Type in Python Binding
    """
    def __init__(self):
        BindingType.__init__(self)


class URIType(BindingType):
    """
    Representation of URI IDL Type in Python Binding
    """
    def __init__(self):
        BindingType.__init__(self)


class EnumType(BindingType):
    """
    Representation of enum IDL Type in Python Binding

    :type name: :class:`str`
    :ivar name: Name of the enum
    :type binding_class: :class:`vmware.vapi.bindings.struct.VapiStruct`
    :ivar binding_class: Reference to the Python native class corresponding
                         to this structure
    """
    def __init__(self, name, binding_class):
        BindingType.__init__(self)
        self._name = name
        self._binding_class = binding_class

    @property
    def name(self):
        """
        Returns the name of the EnumType

        :rtype: :class:`str`
        :return: Name of the EnumType
        """
        return self._name

    @property
    def binding_class(self):
        """
        Returns the reference to the Python native class
        corresponding to this structure
        """
        return self._binding_class


class IdType(BindingType):
    """
    Representation of ID IDL type in Python Binding

    :type resolved_types: :class:`list` of :class:`str` or :class:`str` or
        :class:`None`
    :ivar resolved_types: Resource type(s) for the ID
    :type resource_type_field_name: :class:`str` or :class:`None`
    :ivar resource_type_field_name: Name of the field specifying the resource
        type
    """
    def __init__(self, resource_types=None, resource_type_field_name=None):
        BindingType.__init__(self)
        self._resource_types = resource_types
        self._resource_type_field_name = resource_type_field_name

    @property
    def resource_types(self):
        """
        Returns the Resource type(s) for the ID field

        :rtype: :class:`list` of :class:`str` or :class:`str` or :class:`None`
        :return: Resource type(s) for the ID
        """
        return self._resource_types

    @property
    def resource_type_field_name(self):
        """
        Returns the name of the field specifying the resource type

        :rtype: :class:`str`
        :return: Name of the field specifying the resource type
        """
        return self._resource_type_field_name


class BindingTypeVisitor(VapiVisitor):
    """
    Base no-op implementation of a BindingType visitor
    """
    def __init__(self):
        """
        Initialize BindingTypeVisitor
        """
        VapiVisitor.__init__(self, 'Type')

    def visit_void(self, typ):
        """
        Visit a void value (i.e. None)

        :type  typ: :class:`VoidType`
        :param typ: Binding type of the value
        """
        raise NotImplementedError

    def visit_integer(self, typ):
        """
        Visit an integer value

        :type  typ: :class:`IntegerType`
        :param typ: Binding type of the value
        """
        raise NotImplementedError

    def visit_double(self, typ):
        """
        Visit a double value

        :type  typ: :class:`DoubleType`
        :param typ: Binding type of the value
        """
        raise NotImplementedError

    def visit_string(self, typ):
        """
        Visit a string value

        :type  typ: :class:`StringType`
        :param typ: Binding type of the value
        """
        raise NotImplementedError

    def visit_boolean(self, typ):
        """
        Visit a boolean value

        :type  typ: :class:`BooleanType`
        :param typ: Binding type of the value
        """
        raise NotImplementedError

    def visit_blob(self, typ):
        """
        Visit a blob value

        :type  typ: :class:`BlobType`
        :param typ: Binding type of the value
        """
        raise NotImplementedError

    def visit_optional(self, typ):
        """
        Visit an optional value

        :type  typ: :class:`OptionalType`
        :param typ: Binding type of the value
        """
        raise NotImplementedError

    def visit_list(self, typ):
        """
        Visit a list value

        :type  typ: :class:`ListType`
        :param typ: Binding type of the value
        """
        raise NotImplementedError

    def visit_struct(self, typ):
        """
        Visit a struct value

        :type  typ: :class:`StructType`
        :param typ: Binding type of the value
        """
        raise NotImplementedError

    def visit_dynamic_struct(self, typ):
        """
        Visit a struct value

        :type  typ: :class:`DynamicStructType`
        :param typ: Binding type of the value
        """
        raise NotImplementedError

    def visit_any_error(self, typ):
        """
        Visit an error value

        :type  typ: :class:`AnyErrorType`
        :param typ: Binding type of the value
        """
        raise NotImplementedError

    def visit_opaque(self, typ):
        """
        Visit an opaque value.

        :type  typ: :class:`OpaqueType`
        :param typ: Binding type of the value
        """
        raise NotImplementedError

    def visit_secret(self, typ):
        """
        Visit a secret value

        :type  typ: :class:`SecretType`
        :param typ: Binding type of the value
        """
        raise NotImplementedError

    def visit_date_time(self, typ):
        """
        Visit a datetime value

        :type  typ: :class:`DateTimeType`
        :param typ: Binding type of the value
        """
        raise NotImplementedError

    def visit_uri(self, typ):
        """
        Visit an URI value

        :type  typ: :class:`URIType`
        :param typ: Binding type of the value
        """
        raise NotImplementedError

    def visit_enum(self, typ):
        """
        Visit a enum value

        :type  typ: :class:`EnumType`
        :param typ: Binding type of the value
        """
        raise NotImplementedError

    def visit_error(self, typ):
        """
        Visit an error type

        :type  typ: :class:`ErrorType`
        :param typ: Binding type of the value
        """
        raise NotImplementedError

    def visit_reference(self, typ):
        """
        Visit a reference type

        :type  typ: :class:`ReferenceType`
        :param typ: Binding type of the value
        """
        raise NotImplementedError

    def visit_id(self, typ):
        """
        Visit a ID value

        :type  typ: :class:`IdType`
        :param typ: Binding type of the value
        """
        raise NotImplementedError


class DataDefinitionBuilder(BindingTypeVisitor):
    """
    Builds DataDefinition by visiting a BindingType
    """
    def __init__(self, ctx, seen_structures):
        """
        Initialize DataDefinitionBuilder

        :type  ctx: :class:`vmware.vapi.data.definition.ReferenceResolver`
        :param ctx: Data definition reference resolver object
        :type  seen_structures: :class:`list` or :class:`str`
        :param seen_structures: List of structures seen
        """
        BindingTypeVisitor.__init__(self)
        self._ctx = ctx
        self._seen_structures = seen_structures
        self._out_value = None

    def get_out_value(self):
        """
        Returns the data definition

        :rtype: :class:`vmware.vapi.data.definition.DataDefinition`
        :return: Data definition
        """
        return self._out_value

    def visit_void(self, typ):
        """
        Visit a void value (i.e. None)

        :type  typ: :class:`VoidType`
        :param typ: Binding type of the value
        """
        self._out_value = VoidDefinition()

    def visit_integer(self, typ):
        """
        Visit an integer value

        :type  typ: :class:`IntegerType`
        :param typ: Binding type of the value
        """
        self._out_value = IntegerDefinition()

    def visit_double(self, typ):
        """
        Visit a double value

        :type  typ: :class:`DoubleType`
        :param typ: Binding type of the value
        """
        self._out_value = DoubleDefinition()

    def visit_string(self, typ):
        """
        Visit a string value

        :type  typ: :class:`StringType`
        :param typ: Binding type of the value
        """
        self._out_value = StringDefinition()

    def visit_boolean(self, typ):
        """
        Visit a boolean value

        :type  typ: :class:`BooleanType`
        :param typ: Binding type of the value
        """
        self._out_value = BooleanDefinition()

    def visit_blob(self, typ):
        """
        Visit a blob value

        :type  typ: :class:`BlobType`
        :param typ: Binding type of the value
        """
        self._out_value = BlobDefinition()

    def visit_optional(self, typ):
        """
        Visit an optional value

        :type  typ: :class:`OptionalType`
        :param typ: Binding type of the value
        """
        typ.element_type.accept(self)
        element_def = self._out_value
        self._out_value = OptionalDefinition(element_def)

    def visit_list(self, typ):
        """
        Visit a list value

        :type  typ: :class:`ListType`
        :param typ: Binding type of the value
        """
        typ.element_type.accept(self)
        element_def = self._out_value
        self._out_value = ListDefinition(element_def)

    def visit_set(self, typ):
        """
        Visit a set value

        :type  typ: :class:`SetType`
        :param typ: Binding type of the value
        """
        typ.element_type.accept(self)
        element_def = self._out_value
        self._out_value = ListDefinition(element_def)

    def visit_map(self, typ):
        """
        Visit a map value

        :type  typ: :class:`MapType`
        :param typ: Binding type of the value
        """
        field_defs = []
        typ.key_type.accept(self)
        key_def = self._out_value
        field_defs.append((MAP_KEY_FIELD, key_def))
        typ.value_type.accept(self)
        value_def = self._out_value

        field_defs.append((MAP_VALUE_FIELD, value_def))
        element_def = StructDefinition(MAP_ENTRY, field_defs)
        self._out_value = ListDefinition(element_def)

    def visit_struct(self, typ):
        """
        Visit a struct value

        :type  typ: :class:`StructType`
        :param typ: Binding type of the value
        """
        if typ.name in self._seen_structures:
            if self._ctx.is_defined(typ.name):
                self._out_value = self._ctx.get_definition(typ.name)
            else:
                self._out_value = StructRefDefinition(typ.name)
                self._ctx.add_reference(self._out_value)
        else:
            self._seen_structures.append(typ.name)
            field_defs = []
            for field_name in typ.get_field_names():
                field_type = typ.get_field(field_name)
                field_type.accept(self)
                field_defs.append((field_name, self._out_value))
            self._out_value = StructDefinition(typ.name, field_defs)
            self._ctx.add_definition(self._out_value)

    def visit_dynamic_struct(self, typ):
        """
        Visit a struct value

        :type  typ: :class:`DynamicStructType`
        :param typ: Binding type of the value
        """
        self._out_value = DynamicStructDefinition()

    def visit_any_error(self, typ):
        """
        Visit an error value

        :type  typ: :class:`AnyErrorType`
        :param typ: Binding type of the value
        """
        self._out_value = AnyErrorDefinition()

    def visit_opaque(self, typ):
        """
        Visit an opaque value.

        :type  typ: :class:`OpaqueType`
        :param typ: Binding type of the value
        """
        self._out_value = OpaqueDefinition()

    def visit_secret(self, typ):
        """
        Visit a secret value

        :type  typ: :class:`SecretType`
        :param typ: Binding type of the value
        """
        self._out_value = SecretDefinition()

    def visit_date_time(self, typ):
        """
        Visit a datetime value

        :type  typ: :class:`DateTimeType`
        :param typ: Binding type of the value
        """
        self._out_value = StringDefinition()

    def visit_uri(self, typ):
        """
        Visit an URI value

        :type  typ: :class:`URIType`
        :param typ: Binding type of the value
        """
        self._out_value = StringDefinition()

    def visit_enum(self, typ):
        """
        Visit a enum value

        :type  typ: :class:`EnumType`
        :param typ: Binding type of the value
        """
        self._out_value = StringDefinition()

    def visit_reference(self, typ):
        """
        Visit a reference type

        :type  typ: :class:`ReferenceType`
        :param typ: Binding type of the value
        """
        typ.resolved_type.accept(self)

    def visit_error(self, typ):
        """
        Visit an error type

        :type  typ: :class:`ErrorType`
        :param typ: Binding type of the value
        """
        field_defs = []
        for field_name in typ.get_field_names():
            field_type = typ.get_field(field_name)
            field_type.accept(self)
            field_defs.append((field_name, self._out_value))
        self._out_value = ErrorDefinition(typ.name, field_defs)

    def visit_id(self, typ):
        """
        Visit a ID value

        :type  typ: :class:`IdType`
        :param typ: Binding type of the value
        """
        self._out_value = StringDefinition()


class TypeUtil(object):
    """
    Converts a BindingType object to DataDefinition object
    """

    @staticmethod
    def convert_to_data_definition(binding_type):
        """
        Converts a BindingType object to DataDefinition object

        :type  binding_type: :class:`BindingType`
        :param binding_type: Binding type
        :rtype: :class:`vmware.vapi.data.definition.DataDefinition`
        :return: DataDefinition
        """
        ctx = ReferenceResolver()
        seen_structures = []
        visitor = DataDefinitionBuilder(ctx, seen_structures)
        binding_type.accept(visitor)
        ctx.resolve()
        return visitor.get_out_value()
