"""
DataDefinition classes
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015-2018 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long


from vmware.vapi.data.type import Type
from vmware.vapi.data.value import data_value_factory, StructValue
from vmware.vapi.exception import CoreException
from vmware.vapi.l10n.runtime import message_factory
from vmware.vapi.lib.constants import MAP_ENTRY, OPERATION_INPUT
from vmware.vapi.lib.log import get_vapi_logger
from vmware.vapi.lib.visitor import VapiVisitor

logger = get_vapi_logger(__name__)


class DataDefinition(object):
    """
    Base class for all types in the vAPI run-time type system

    :type type: :class:`str`
    :ivar type: String representation of the type
    """
    def __init__(self, data_type=None):
        """
        Initialize the data definition instance

        :type  data_type: :class:`str`
        :param data_type: String representation of the type
        """
        self.type = data_type

    def valid_instance_of(self, value):
        """
        Validates that the specified :class:`vmware.vapi.data.value.DataValue`
        is an instance of this data-definition

        :type  value: :class:`vmware.vapi.data.value.DataValue`
        :param value: the data value to validate

        :rtype: :class:`bool`
        :return: true if the value is an instance of this data-definition,
                 false, otherwise
        """
        return not self.validate(value)

    def validate(self, value):
        """
        Validates that the specified :class:`vmware.vapi.data.value.DataValue`
        is an instance of this data-definition

        :type  value: :class:`vmware.vapi.data.value.DataValue`
        :param value: the data value to validate

        :rtype: :class:`list` of :class:`vmware.vapi.message.Message`
                or ``None``
        :return: a stack of messages indicating why the value is not an instance
                 of this data-definition, or None if the value is an instance of
                 this data-definition
        """
        if value is None:
            msg = message_factory.get_message('vapi.data.validate.mismatch',
                                              self.type,
                                              'None')
            return [msg]

        if value.type != self.type:
            msg = message_factory.get_message('vapi.data.validate.mismatch',
                                              self.type,
                                              value.type)
            return [msg]

        return None

    def complete_value(self, value):
        """
        Fill the optional fields of StructValues. Also
        includes the StructValues present in other generic types: List
        and Optional.

        :type  value: :class:`vmware.vapi.data.value.DataValue`
        :param value: DataValue
        """
        return None

    def accept(self, visitor):
        """
        Applies a visitor to this data-definition.

        :type  visitor: :class:`SimpleDefinitionVisitor`
        :param visitor: the visitor operating on this data-definition
        """
        visitor.visit(self)

    def __eq__(self, other):
        if not isinstance(other, DataDefinition):
            return NotImplemented

        return self.type == other.type

    def __ne__(self, other):
        if not isinstance(other, DataDefinition):
            return NotImplemented
        return not (self == other)

    # Classes that override __eq__ should define __hash__ to make
    # its instances usable in hashed collections
    def __hash__(self):
        return str(self).__hash__()

    def __repr__(self):
        return '%s()' % self.__class__.__name__


class SingletonDefinition(DataDefinition):
    """
    Base class for all the primitive data definition classes. All the derived
    classes of this class will have only one instance.
    """
    _instance = None

    def __init__(self, data_type):
        """
        Initialize SingletonDefinition

        :type  data_type: :class:`vmware.vapi.data.type.Type`
        :param data_type: Type of the DataDefinition
        """
        DataDefinition.__init__(self, data_type)

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SingletonDefinition, cls).__new__(
                cls, *args, **kwargs)
        return cls._instance


class VoidDefinition(SingletonDefinition):
    """
    DataDefinition class for void
    """
    def __init__(self):
        """
        Initialize VoidDefinition
        """
        SingletonDefinition.__init__(self, Type.VOID)

    def new_value(self):
        """
        Create a new VoidValue

        :rtype: :class:`vmware.vapi.data.value.VoidValue`
        :return: Newly created VoidValue
        """
        return data_value_factory(self.type)


class IntegerDefinition(SingletonDefinition):
    """
    DataDefinition for long values
    """
    def __init__(self):
        """
        Initialize IntegerDefinition
        """
        SingletonDefinition.__init__(self, Type.INTEGER)

    def new_value(self, value=0):
        """
        Create a new IntegerValue

        :rtype: :class:`vmware.vapi.data.value.IntegerValue`
        :return: Newly created IntegerValue
        """
        return data_value_factory(self.type, value)


class DoubleDefinition(SingletonDefinition):
    """
    DataDefinition for floats
    """
    def __init__(self):
        """
        Initialize DoubleDefinition
        """
        SingletonDefinition.__init__(self, Type.DOUBLE)

    def new_value(self, value=0.0):
        """
        Create a new DoubleValue

        :rtype: :class:`vmware.vapi.data.value.DoubleValue`
        :return: Newly created DoubleValue
        """
        return data_value_factory(self.type, value)


class StringDefinition(SingletonDefinition):
    """
    DataDefinition for strings
    """
    def __init__(self):
        """
        Initialize StringDefinition
        """
        SingletonDefinition.__init__(self, Type.STRING)

    def new_value(self, value=""):
        """
        Create a new StringValue

        :rtype: :class:`vmware.vapi.data.value.StringValue`
        :return: Newly created StringValue
        """
        return data_value_factory(self.type, value)


class OpaqueDefinition(SingletonDefinition):
    """
    DataDefinition for opaque
    """
    def __init__(self):
        """
        Initialize OpaqueDefinition
        """
        SingletonDefinition.__init__(self, Type.OPAQUE)

    def validate(self, value):
        """
        The validation for OpaqueDefinition will succeed against
        any DataValue. Only validates that supplied value is not None

        :type  value: :class:`vmware.vapi.data.value.DataValue`
        :param value: DataValue to be validated
        :rtype: :class:`list` of :class:`vmware.vapi.message.Message`
                 or ``None``
        :return: a stack of messages indicating why the value is not an instance
                 of this data-definition, or None if the value is an instance of
                 this data-definition
        """
        if value is None:
            msg = message_factory.get_message('vapi.data.validate.mismatch',
                                              self.type,
                                              'None')
            return [msg]
        return None


class DynamicStructDefinition(SingletonDefinition):
    """
    DataDefinition for dynamic structs
    """
    _valid_types = [Type.STRUCTURE, Type.ERROR]

    def __init__(self):
        """
        Initialize DynamicStructDefinition
        """
        SingletonDefinition.__init__(self, Type.DYNAMIC_STRUCTURE)

    def validate(self, value):
        """
        The validation for DynamicStructDefinition will succeed against
        any StructValue.

        :type  value: :class:`vmware.vapi.data.value.DataValue`
        :param value: the data value to validate

        :rtype: :class:`list` of :class:`vmware.vapi.message.Message`
                or ``None``
        :return: a stack of messages indicating why the value is not an instance
                 of this data-definition, or None if the value is an instance of
                 this data-definition
        """
        if value is None:
            msg = message_factory.get_message(
                'vapi.data.dynamicstruct.validate.mismatch',
                self._valid_types,
                'None')
            return [msg]

        if value.type not in self._valid_types:
            msg = message_factory.get_message(
                'vapi.data.dynamicstruct.validate.mismatch',
                self._valid_types,
                value.type)
            return [msg]

        return None


class AnyErrorDefinition(SingletonDefinition):
    """
    DataDefinition for 'Exception' type in IDL
    """
    def __init__(self):
        """
        Initialize AnyErrorDefinition
        """
        SingletonDefinition.__init__(self, Type.ANY_ERROR)

    def validate(self, value):
        """
        The validation for AnyErrorDefinition will succeed against
        any ErrorValue.

        :type  value: :class:`vmware.vapi.data.value.DataValue`
        :param value: the data value to validate

        :rtype: :class:`list` of :class:`vmware.vapi.message.Message`
                or ``None``
        :return: a stack of messages indicating why the value is not an instance
                 of this data-definition, or None if the value is an instance of
                 this data-definition
        """
        if value is None:
            msg = message_factory.get_message('vapi.data.validate.mismatch',
                                              self.type,
                                              'None')
            return [msg]

        if value.type != Type.ERROR:
            msg = message_factory.get_message('vapi.data.validate.mismatch',
                                              self.type,
                                              value.type)
            return [msg]

        return None


class BlobDefinition(SingletonDefinition):
    """
    DataDefinition for binary values
    """
    def __init__(self):
        """
        Initialize BlobDefinition
        """
        SingletonDefinition.__init__(self, Type.BLOB)

    def new_value(self, value=b''):
        """
        Create a new BlobValue

        :rtype: :class:`vmware.vapi.data.value.BlobValue`
        :return: Newly created BlobValue
        """
        return data_value_factory(self.type, value)


class BooleanDefinition(SingletonDefinition):
    """
    DataDefinition for bool values
    """
    def __init__(self):
        """
        Initialize BooleanDefinition
        """
        SingletonDefinition.__init__(self, Type.BOOLEAN)

    def new_value(self, value=False):
        """
        Create a new BooleanValue

        :rtype: :class:`vmware.vapi.data.value.BooleanValue`
        :return: Newly created BooleanValue
        """
        return data_value_factory(self.type, value)


class ListDefinition(DataDefinition):
    """
    DataDefinition for lists
    """
    def __init__(self, element_type):
        """
        Initialize ListDefinition

        :type  element_type: :class:`DataDefinition`
        :param element_type: DataDefinition of the elements inside
                ListDefinition
        """
        if not element_type:
            raise ValueError('ListDefinition requires element definition')
        DataDefinition.__init__(self, Type.LIST)
        self.element_type = element_type

    def new_value(self, values=None):
        """
        Create a new ListValue

        :type  values: :class:`list` of
                :class:`vmware.vapi.data.value.DataValue`
        :param values: List of elements
        :rtype: :class:`vmware.vapi.data.value.ListValue`
        :return: Newly created ListValue
        """
        return data_value_factory(self.type, values)

    def validate(self, list_value):
        """
        Apart from the validation checks specified in the validate
        method of DataDefinition class, this method does some additional checks

        Validation will fail if any element in the ListValue does not validate
        against the DataDefinition of the elementType of this ListDefinition

        :type  other: :class:`vmware.vapi.data.value.ListValue`
        :param other: ListValue to be validated
        :rtype: :class:`list` of :class:`vmware.vapi.message.Message`
                or ``None``
        :return: a stack of messages indicating why the value is not an instance
                 of this data-definition, or None if the value is an instance of
                 this data-definition
        """
        if isinstance(list_value, StructValue):
            return None

        errors = DataDefinition.validate(self, list_value)
        if errors:
            return errors

        for index, value in enumerate(list_value):
            errors = self.element_type.validate(value)
            if errors:
                msg = message_factory.get_message(
                    'vapi.data.list.invalid.entry',
                    str(value), index)
                return [msg] + errors

        return None

    def complete_value(self, value):
        """
        Fill the optional values inside StructValues

        :type  value: :class:`vmware.vapi.data.value.DataValue`
        :param value: DataValue
        """
        if value.type == Type.STRUCTURE:
            return None
        assert(value.type == Type.LIST)

        for element in value:
            self.element_type.complete_value(element)
        return None

    def __eq__(self, other):
        if not isinstance(other, ListDefinition):
            return NotImplemented

        return (DataDefinition.__eq__(self, other)
                and self.element_type == other.element_type)

    # Classes that override __eq__ should define __hash__ to make
    # its instances usable in hashed collections
    def __hash__(self):
        return DataDefinition.__hash__(self)

    def __repr__(self):
        return 'ListDefinition(element_type=%s)' % repr(self.element_type)


class StructDefinition(DataDefinition):
    """
    DataDefinition for structures
    """
    def __init__(self, name, fields, data_type=Type.STRUCTURE):
        """
        Initialize StructDefinition

        :type  name: :class:`str`
        :param name: Name of the Structure
        :type  fields: :class:`tuple` of (:class:`str`, :class:`DataDefinition`)
        :param fields: A tuple consisting of the field name and the field
                       definition for all the fields inside this
                       StructDefinition
        """
        if not name:
            raise ValueError('Struct name may not be None or empty string')
        DataDefinition.__init__(self, data_type)
        self.name = name
        self._keys = [k for (k, _) in fields]
        self._dict = dict(fields)

    def new_value(self):
        """
        Create a new StructValue

        :rtype: :class:`vmware.vapi.data.value.StructValue`
        :return: Newly created StructValue
        """
        return data_value_factory(self.type, self.name)

    def get_field_names(self):
        """
        Returns the list of field names in this struct definition. The ordering
        of fields is not preserved.

        :rtype: :class:`list` of :class:`str`
        :return: List of field names in this struct definition
        """
        return self._keys

    def get_field(self, field):
        """
        Returns the field definition of the specified field

        :rtype: :class:`DataDefinition`
        :return: field definition of the specified field
        """
        return self._dict.get(field)

    def validate(self, other):
        """
        Apart from the validation checks specified in the validate
        method of DataDefinition class, this method does some additional checks

        Validation will fail if
        - the name of the input StructValue does not match the name of this
        StructDefinition.
        - any of the fields (either required or optional) in this
        StructDefinition are not present in the input StructValue
        - the validation fails for any field value in the input StructValue with
        its corresponding definition in this StructDefinition

        The method performs inclusive validation. i.e. If there are any extra
        fields in the input StructValue which are not present in the
        StructDefinition, validation will not fail.

        :type  other: :class:`vmware.vapi.data.value.StructValue`
        :param other: StructValue to be validated
        :rtype: :class:`list` of :class:`vmware.vapi.message.Message`
                or ``None``
        :return: a stack of messages indicating why the value is not an instance
                 of this data-definition, or None if the value is an instance of
                 this data-definition
        """
        errors = DataDefinition.validate(self, other)
        if errors:
            return errors

        if (other.name != self.name):
            # Remove the following if condition in R28
            # To handle old client talking to new server
            if self.name in [MAP_ENTRY, OPERATION_INPUT]:
                pass
            else:
                msg = message_factory.get_message(
                    'vapi.data.structure.name.mismatch',
                    self.name, other.name)
                logger.debug(msg)
                return [msg]

        for field in self._keys:
            if (not other.has_field(field)
                    and self._dict.get(field).type != Type.OPTIONAL):
                msg = message_factory.get_message(
                    'vapi.data.structure.field.missing',
                    self.name, field)
                logger.debug(msg)
                return [msg]

            field_def = self._dict.get(field)
            field_val = other.get_field(field)
            errors = field_def.validate(field_val)
            if errors:
                msg = message_factory.get_message(
                    'vapi.data.structure.field.invalid',
                    field, self.name)
                logger.debug(msg)
                return [msg] + errors

        return None

    def complete_value(self, value):
        """
        Fill out all the unset optional fields in a structure
        based on the StructDefinition

        :type  value: :class:`vmware.vapi.data.value.StructValue`
        :param value: Input Struct Value
        """
        assert(value.type == self.type)
        assert(value is not None)

        for field in self._keys:
            field_def = self.get_field(field)
            if value.has_field(field):
                # Complete the optional values in elements as well
                field_def.complete_value(value.get_field(field))
            elif field_def.type == Type.OPTIONAL:
                # If field is not present and it is optional, fill it
                value.set_field(field, field_def.new_value())

    def __eq__(self, other):
        if not isinstance(other, StructDefinition):
            return NotImplemented

        if not (DataDefinition.__eq__(self, other) and other.name == self.name):
            return False

        for field in self._keys:
            other_field_def = other.get_field(field)
            if not other_field_def:
                return False
            field_def = self.get_field(field)
            if field_def != other_field_def:
                return False

        return True

    # Classes that override __eq__ should define __hash__ to make
    # its instances usable in hashed collections
    def __hash__(self):
        return DataDefinition.__hash__(self)

    def __repr__(self):
        fields = ", ".join(["%s=%s" % (field, repr(self._dict.get(field)))
                           for field in sorted(self._keys)])
        return '%s(name=%s, fields={%s})' % (self.__class__.__name__,
                                             repr(self.name),
                                             fields)


class StructRefDefinition(DataDefinition):
    """
    Reference to a StructDefinition. If the reference is resolved, it is
    bound to a specific StructDefinition target. If the reference is
    unresolved, its target is None.

    :type name: :class:`str`
    :ivar name: Structure name
    """
    def __init__(self, name, definition=None):
        """
        Initialize StructRefDefinition

        :type  name: :class:`str`
        :param name: Structure name
        :type  definition: :class:`DataDefinition`
        :param definition: If definition is passed, it creates a resolved
                           reference
        """
        if not name:
            raise ValueError('Struct name may not be None or empty string')
        self.name = name
        self._definition = definition
        DataDefinition.__init__(self, Type.STRUCTURE_REF)

    @property
    def target(self):
        """
        Returns the target structure definition of this reference.

        :rtype: :class:`DataDefinition` or ``None``
        :return: The target of this reference. The value will be None for
                 unresolved reference
        """
        return self._definition

    @target.setter
    def target(self, definition):
        """
        Resolves the reference. An unresolved reference can be resolved exactly
        once. A resolved reference cannot be re-resolved.

        :type  definition: :class:`DataDefinition`
        :param definition: structure definition
        :raise: :class:`vmware.vapi.exception.CoreException`: if the reference
            is already resolved (already has) a target) or if the name of the
            reference does not match the name of the definition
        """
        if not definition:
            raise ValueError('StructDefinition may not be None')
        if self._definition:
            msg = message_factory.get_message(
                'vapi.data.structref.already.resolved', self.name)
            logger.debug(msg)
            raise CoreException(msg)
        if self.name != definition.name:
            msg = message_factory.get_message(
                'vapi.data.structref.resolve.type.mismatch',
                self.name, definition.name)
            logger.debug(msg)
            raise CoreException(msg)
        self._definition = definition

    def check_resolved(self):
        """
        Check if the reference is resolved or not
        """
        if self._definition is None:
            msg = message_factory.get_message(
                'vapi.data.structref.not.resolved',
                self.name)
            logger.debug(msg)
            raise CoreException(msg)

    def complete_value(self, value):
        """
        Fill out all the unset optional fields in a structure
        based on the resolved StructDefinition for this
        StructRefDefinition.

        :type  value: :class:`vmware.vapi.data.value.StructValue`
        :param value: Input StructValue
        """
        self.check_resolved()
        self._definition.complete_value(value)

    def validate(self, other):
        """
        Validate using the target if the reference is resolved

        :type  other: :class:`vmware.vapi.data.value.StructValue`
        :param other: StructValue to be validated
        :rtype: :class:`list` of :class:`vmware.vapi.message.Message` of
                ``None``
        :return: a stack of messages indicating that the reference is not
                 resolved or why the value is not an instance of this
                 data-definition, or None if the value is an instance of
                 this data-definition
        """
        try:
            self.check_resolved()
        except CoreException as err:
            return err.messages
        return self._definition.validate(other)

    def __eq__(self, other):
        if not isinstance(other, StructRefDefinition):
            return NotImplemented

        if not (DataDefinition.__eq__(self, other)
                and other.name == self.name):
            return False

        return True

    # Classes that override __eq__ should define __hash__ to make
    # its instances usable in hashed collections
    def __hash__(self):
        return DataDefinition.__hash__(self)

    def __repr__(self):
        return 'StructRefDefinition(name=%s)' % self.name


class ErrorDefinition(StructDefinition):
    """
    DataDefinition for errors
    """
    def __init__(self, name, fields):
        """
        Initialize ErrorDefinition

        :type  name: :class:`str`
        :param name: Name of the Error
        :type  fields: :class:`tuple` of (:class:`str`, :class:`DataDefinition`)
        :param fields: A tuple consisting of the field name and the field
                       definition for all the fields inside this
                       StructDefinition
        """
        StructDefinition.__init__(self, name, fields, Type.ERROR)

    def new_value(self):
        """
        Create a new ErrorValue

        :rtype: :class:`vmware.vapi.data.value.ErrorValue`
        :return: Newly created ErrorValue
        """
        return data_value_factory(self.type, self.name)


class OptionalDefinition(DataDefinition):
    """
    An OptionalDefinition instance defines an optional type with a specified
    element type

    :type data_type: :class:`str`
    :ivar type: String representation of the type
    :type element_type: :class:`DataDefinition`
    :ivar element_type: The type of the element that is optional
    """
    def __init__(self, element_type):
        """
        Initialize OptionalDefinition

        :type  element_type: :class:`vmware.vapi.data.type.Type`
        :param element_type: Type of the DataDefinition
        """
        if not element_type:
            raise ValueError('Optional definition requires element definition')
        DataDefinition.__init__(self, Type.OPTIONAL)
        self.element_type = element_type

    def new_value(self, value=None):
        """
        Create and return a new :class:`OptionalValue` using this
        optional-definition.

        :type  value: :class:`vmware.vapi.data.value.DataValue`
        :param value: The element value

        :rtype: :class:`vmware.vapi.data.value.OptionalValue`
        :return: A new optional value using the given data-definition
        """
        return data_value_factory(self.type, value)

    def validate(self, value):
        """
        Apart from the validation checks specified in the validate
        method of DataDefinition class, this method does some additional checks.

        Since this is an OptionalValue, validation will succeed if the
        element value is None. If the element value is not None, validation
        will fail if element in the OptionalValue does not validate against
        the DataDefinition of the element_type of this OptionalDefinition.

        :type  other: :class:`vmware.vapi.data.value.OptionalValue`
        :param other: OptionalValue to be validated
        :rtype: :class:`list` of :class:`vmware.vapi.message.Message`
        :return: a stack of messages indicating why the value is not an instance
                 of this data-definition, or None if the value is an instance of
                 this data-definition
        """
        errors = DataDefinition.validate(self, value)
        if errors:
            return errors

        if value.value is None:
            # None is a valid value for optional
            pass
        elif value.is_set():
            errors = self.element_type.validate(value.value)
            if errors:
                msg = message_factory.get_message('vapi.data.optional.validate')
                return [msg] + errors

        return None

    def complete_value(self, value):
        """
        Fill the optional values inside StructValues

        :type  value: :class:`vmware.vapi.data.value.OptionalValue`
        :param value: DataValue
        """
        assert(value.type == Type.OPTIONAL)
        if value.is_set():
            self.element_type.complete_value(value.value)

    def __eq__(self, other):
        if not isinstance(other, OptionalDefinition):
            return NotImplemented

        return (DataDefinition.__eq__(self, other)
                and self.element_type == other.element_type)

    # Classes that override __eq__ should define __hash__ to make
    # its instances usable in hashed collections
    def __hash__(self):
        return DataDefinition.__hash__(self)

    def __repr__(self):
        return "OptionalDefinition(element_type=%s)" % repr(self.element_type)


class SecretDefinition(SingletonDefinition):
    """
    DataDefinition for Secrets. Only strings are allowed to be secrets.
    """
    def __init__(self):
        """
        Initialize SecretDefinition
        """
        SingletonDefinition.__init__(self, Type.SECRET)

    def new_value(self, value=""):
        """
        Create a new SecretValue

        :rtype: :class:`vmware.vapi.data.value.SecretValue`
        :return: Newly created SecretValue
        """
        return data_value_factory(self.type, value)


class SimpleDefinitionVisitor(VapiVisitor):
    """
    Base no-op implementation of a definition visitor
    """
    def __init__(self):
        VapiVisitor.__init__(self, 'Definition')

    def visit_void(self, defn):
        """
        Visit a VoidDefinition

        :type  defn: :class:`VoidDefinition`
        :param defn: Data definition
        """
        raise NotImplementedError

    def visit_integer(self, defn):
        """
        Visit a IntegerDefinition

        :type  defn: :class:`IntegerDefinition`
        :param defn: Data definition
        """
        raise NotImplementedError

    def visit_double(self, defn):
        """
        Visit a DoubleDefinition

        :type  defn: :class:`DoubleDefinition`
        :param defn: Data definition
        """
        raise NotImplementedError

    def visit_string(self, defn):
        """
        Visit a StringDefinition

        :type  defn: :class:`StringDefinition`
        :param defn: Data definition
        """
        raise NotImplementedError

    def visit_opaque(self, defn):
        """
        Visit a OpaqueDefinition

        :type  defn: :class:`OpaqueDefinition`
        :param defn: Data definition
        """
        raise NotImplementedError

    def visit_blob(self, defn):
        """
        Visit a BlobDefinition

        :type  defn: :class:`BlobDefinition`
        :param defn: Data definition
        """
        raise NotImplementedError

    def visit_boolean(self, defn):
        """
        Visit a BooleanDefinition

        :type  defn: :class:`BooleanDefinition`
        :param defn: Data definition
        """
        raise NotImplementedError

    def visit_list(self, defn):
        """
        Visit a ListDefinition

        :type  defn: :class:`ListDefinition`
        :param defn: Data definition
        """
        raise NotImplementedError

    def visit_struct(self, defn):
        """
        Visit a StructDefinition

        :type  defn: :class:`StructDefinition`
        :param defn: Data definition
        """
        raise NotImplementedError

    def visit_error(self, defn):
        """
        Visit an ErrorDefinition

        :type  defn: :class:`ErrorDefinition`
        :param defn: Data definition
        """
        raise NotImplementedError

    def visit_optional(self, defn):
        """
        Visit a OptionalDefinition

        :type  defn: :class:`OptionalDefinition`
        :param defn: Data definition
        """
        raise NotImplementedError

    def visit_secret(self, defn):
        """
        Visit a SecretDefinition

        :type  defn: :class:`SecretDefinition`
        :param defn: Data definition
        """
        raise NotImplementedError

    def visit_struct_ref(self, defn):
        """
        Visit a StructRefDefinition

        :type  defn: :class:`StructRefDefinition`
        :param defn: StructRefDefinition object
        """
        raise NotImplementedError


# vapi type name to vapi type definition map
data_type_to_definition_map = {
    Type.INTEGER: IntegerDefinition,
    Type.DOUBLE: DoubleDefinition,
    Type.BOOLEAN: BooleanDefinition,
    Type.STRING: StringDefinition,
    Type.BLOB: BlobDefinition,
    Type.LIST: ListDefinition,
    Type.STRUCTURE: StructDefinition,
    Type.OPTIONAL: OptionalDefinition,
    Type.VOID: VoidDefinition,
    Type.OPAQUE: OpaqueDefinition,
    Type.SECRET: SecretDefinition,
    Type.ERROR: ErrorDefinition,
    Type.STRUCTURE_REF: StructRefDefinition,
    Type.DYNAMIC_STRUCTURE: DynamicStructDefinition,
}


def data_definition_factory(data_type, *args, **kwargs):
    """
    data definition factory

    :type  data_type: :class:`str`
    :param data_type: Type name defined in vmware.vapi.data.type
    :type  args: :class:`set`
    :param args: Positional arguments to data definition constructor
    :type  kwargs: :class:`dict`
    :param kwargs: Dict arguments to data definition constructor
    """
    constructor = data_type_to_definition_map.get(data_type)
    return constructor(*args, **kwargs)


class ReferenceResolver(object):
    """
    Resolves all the StructRefDefinition objects
    """
    def __init__(self):
        """
        Initialize ReferenceResolver
        """
        self._definitions = {}
        self._references = []

    def add_definition(self, definition):
        """
        Adds a new structure definition to the context

        :type  definition: :class:`StructDefinition`
        :param definition: StructDefinition
        """
        self._definitions[definition.name] = definition

    def add_reference(self, reference):
        """
        Adds a new structure refernce to the context

        :type  refernce: :class:`StructRefDefinition`
        :param refernce: StructRefDefinition
        """
        self._references.append(reference)

    def is_defined(self, name):
        """
        Determines whether the context contains a definition for the specified
        structure

        :rtype: :class:`bool`
        :return: True if the structure is already defined, false otherwise
        """
        return name in self._definitions

    def get_definition(self, name):
        """
        Determines whether the context contains a definition for the specified
        structure

        :rtype: :class:`StructDefinition`
        :return: Definition if the structure if it is already defined,
                 None otherwise
        """
        if self.is_defined(name):
            return self._definitions[name]
        return None

    def resolve(self):
        """
        Traverses all references and resolves the unresolved ones.
        """
        for reference in self._references:
            if reference.target is None:
                definition = self._definitions.get(reference.name)
                if definition is None:
                    msg = message_factory.get_message(
                        'vapi.data.structref.structure.not.defined',
                        reference.name)
                    logger.debug(msg)
                    raise CoreException(msg)
                reference.target = definition
