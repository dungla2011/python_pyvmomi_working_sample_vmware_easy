"""
vAPI DataValues
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015-2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import math
import six
from decimal import Decimal

from vmware.vapi.data.type import Type
from vmware.vapi.exception import CoreException
from vmware.vapi.l10n.runtime import message_factory
from vmware.vapi.lib.visitor import VapiVisitor
from vmware.vapi.lib.log import get_vapi_logger

logger = get_vapi_logger(__name__)


class DataValue(object):
    """
    A piece of introspectable value in vAPI infrastructure

    :type type: :class:`vmware.vapi.data.type.Type`
    :ivar type: Type of DataValue
    """
    def __init__(self, data_type=None):
        """
        Initialize DataValue

        :type  data_type: :class:`vmware.vapi.data.type.Type`
        :param data_type: Type of DataValue
        """
        self.type = data_type

    def accept(self, visitor):
        """
        Applies a visitor to this DataValue

        :type  visitor: :class:`SimpleValueVisitor`
        :param visitor: visitor operating on this DataValue
        """
        visitor.visit(self)


class PrimitiveDataValue(DataValue):
    """
    Base class for all primitive DataValues

    :type value: :class:`object`
    :ivar value: Primitive value
    """
    def __init__(self, *args, **kwargs):
        DataValue.__init__(self, *args, **kwargs)
        self.value = None

    def __repr__(self):
        return '%s(value=%s)' % (self.__class__.__name__,
                                 repr(self.value))


class ComparableValueMixin(object):
    """
    Helper class to implement the rich comparator operations.
    """
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.value == other.value
        else:
            return NotImplemented

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return self.value != other.value
        else:
            return NotImplemented

    def __lt__(self, other):
        if isinstance(other, self.__class__):
            return self.value < other.value
        else:
            return NotImplemented

    def __gt__(self, other):
        if isinstance(other, self.__class__):
            return self.value > other.value
        else:
            return NotImplemented

    def __le__(self, other):
        if isinstance(other, self.__class__):
            return self.value <= other.value
        else:
            return NotImplemented

    def __ge__(self, other):
        if isinstance(other, self.__class__):
            return self.value >= other.value
        else:
            return NotImplemented

    def __hash__(self):
        return hash(self.value)


class IntegerValue(PrimitiveDataValue, ComparableValueMixin):
    """
    DataValue class for integer values

    :type value: :class:`int`
    :ivar value: 64 bit signed int present in IntegerValue
    """
    def __init__(self, value=0):
        """
        Initialize IntegerValue

        :type  value: :class:`int`
        :kwarg value: Integer value to be initialized
        """
        PrimitiveDataValue.__init__(self, Type.INTEGER)
        ComparableValueMixin.__init__(self)
        if not isinstance(value, six.integer_types):
            msg = message_factory.get_message("vapi.data.invalid",
                                              self.type,
                                              type(value).__name__)
            logger.debug(msg)
            raise CoreException(msg)
        self.value = value


class DoubleValue(PrimitiveDataValue, ComparableValueMixin):
    """
    DataValue class for float values

    :type value: :class:`float` or :class:`decimal.Decimal`
    :ivar value: 64 bit signed float present in DoubleValue
    """
    def __init__(self, value=0.0):
        """
        Initialize DoubleValue

        :type  value: :class:`float` or :class:`decimal.Decimal`
        :kwarg value: Float or decimal.Decimal value to be initialized
        """
        PrimitiveDataValue.__init__(self, Type.DOUBLE)
        ComparableValueMixin.__init__(self)
        if not isinstance(value, float) and not isinstance(value, Decimal):
            msg = message_factory.get_message('vapi.data.invalid',
                                              self.type,
                                              type(value).__name__)
            logger.debug(msg)
            raise CoreException(msg)
        # Accept floats, but store as decimal
        if isinstance(value, float):
            value = Decimal(str(value))
        if isinstance(value, Decimal):
            if math.isinf(float(value)):
                msg = message_factory.get_message(
                        'vapi.data.invalid.double.inf', value)
                logger.debug(msg)
                raise CoreException(msg)
        self.value = value


class StringValue(PrimitiveDataValue, ComparableValueMixin):
    """
    DataValue class for strings

    :type value: :class:`str`
    :ivar value: String present in StringValue
    """
    def __init__(self, value=""):
        """
        Initialize StringValue

        :type  value: :class:`str` or :class:`unicode` for Python 2 and
                      :class:`str` for Python 3
        :kwarg value: String value to be initialized
        """
        PrimitiveDataValue.__init__(self, Type.STRING)
        ComparableValueMixin.__init__(self)
        if not isinstance(value, six.string_types):
            msg = message_factory.get_message("vapi.data.invalid",
                                              self.type,
                                              type(value).__name__)
            logger.debug(msg)
            raise CoreException(msg)
        self.value = value


class BooleanValue(PrimitiveDataValue, ComparableValueMixin):
    """
    DataValue class for bool values

    :type value: :class:`bool`
    :ivar value: Bool present in BooleanValue
    """
    def __init__(self, value=False):
        """
        Initialize BooleanValue

        :type  value: :class:`bool`
        :kwarg value: Bool value to be initialized
        """
        PrimitiveDataValue.__init__(self, Type.BOOLEAN)
        ComparableValueMixin.__init__(self)
        if not isinstance(value, bool):
            msg = message_factory.get_message("vapi.data.invalid",
                                              self.type,
                                              type(value).__name__)
            logger.debug(msg)
            raise CoreException(msg)
        self.value = value


class BlobValue(PrimitiveDataValue, ComparableValueMixin):
    """
    DataValue class for binary values

    :type value: :class:`str` for Python 2 and :class:`bytes` for Python 3
    :ivar value: Binary present in BlobValue
    """
    def __init__(self, value=b''):
        """
        Initialize BooleanValue

        :type value: :class:`str` for Python 2 and :class:`bytes` for Python 3
        :kwarg value: Binary value to be initialized
        """
        PrimitiveDataValue.__init__(self, Type.BLOB)
        ComparableValueMixin.__init__(self)
        if not isinstance(value, six.binary_type):
            msg = message_factory.get_message("vapi.data.invalid",
                                              self.type,
                                              type(value).__name__)
            logger.debug(msg)
            raise CoreException(msg)
        self.value = value


class VoidValue(PrimitiveDataValue):
    """
    DataValue class for None
    """
    def __init__(self):
        """
        Initialize VoidValue
        """
        PrimitiveDataValue.__init__(self, Type.VOID)

    def __eq__(self, other):
        if isinstance(other, VoidValue):
            return True
        else:
            return False

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash(None)

    def __repr__(self):
        return 'VoidValue()'


class ListValue(DataValue):
    """
    DataValue class for lists
    """
    def __init__(self, values=None, is_map=False):
        """
        Initialize ListValue
        """
        DataValue.__init__(self, Type.LIST)
        if values is not None and not isinstance(values, list):
            msg = message_factory.get_message("vapi.data.invalid",
                                              self.type,
                                              type(values).__name__)
            logger.debug(msg)
            raise CoreException(msg)
        self._list_val = values if values is not None else []
        self._is_map = is_map

    def add(self, value):
        """
        Add an element to ListValue

        :type  value: :class:`DataValue`
        :param value: DataValue to be added
        """
        self._list_val.append(value)

    def add_all(self, values):
        """
        Add all the elements from input list to ListValue

        :type  values: :class:`list` of :class:`DataValue`
        :param values: List of DataValues to be added
        """
        for value in values:
            self.add(value)

    def is_empty(self):
        """
        Returns true if the list is empty

        :rtype: :class:`bool`
        :return: True if the list is empty, false otherwise
        """
        return not self._list_val

    def size(self):
        """
        Returns the size of the list

        :rtype: :class:`int`
        :return: Size of the list value
        """
        return len(self._list_val)

    def is_map(self):
        """
        Returns true if the list is representing a VMODL2 map type

        :rtype: :class:`bool`
        :return: True if the list is representing a map, false otherwise
        """
        return self._is_map

    def set_map(self, is_map):
        """
        Sets if this List Value is used to represent a map
        """
        self._is_map = is_map

    def __eq__(self, other):
        if not isinstance(other, ListValue):
            return False

        if self.size() != other.size():
            return False

        for self_item, other_item in zip(self, other):
            if self_item != other_item:
                return False

        return True

    def __ne__(self, other):
        return not (self == other)

    def __iter__(self):
        return self._list_val.__iter__()

    def __len__(self):
        return len(self._list_val)

    def __repr__(self):
        ret = ', '.join([repr(val) for val in self._list_val])
        return 'ListValue(values=[%s], is_map=%s)' % (ret, self._is_map)


class OptionalValue(DataValue, ComparableValueMixin):
    """
    DataValue class for optionals

    :type value: :class:`DataValue`
    :ivar value: DataValue present in this OptionalValue
    """
    def __init__(self, value=None):
        """
        Initialize OptionalValue

        :type  value: :class:`DataValue`
        :kwarg value: DataValue to be used in OptionalValue
        """
        DataValue.__init__(self, Type.OPTIONAL)
        ComparableValueMixin.__init__(self)
        self.value = value

    def is_set(self):
        """
        Returns true if OptionalValue has a DataValue present in it

        :rtype: :class:`bool`
        :return: Returns true if OptionalValue is initialized with some
                 DataValue, false otherwise
        """
        return self.value is not None

    def __repr__(self):
        return 'OptionalValue(%s)' % repr(self.value)


class StructValue(DataValue):
    """
    DataValue class for Structures

    :type name: :class:`str`
    :ivar name: Name of the structure
    """
    def __init__(self, name=None, data_type=Type.STRUCTURE, values=None):
        """
        Initialize StructValue

        :type  name: :class:`str` or :class:`unicode` for Python 2
        :kwarg name: Name of the StructValue
        :type  data_type: :class:`str`
        :kwarg data_type: Type of StructValue, whether structure or error.
        :type  values: :class:`dict` of :class:`str` and :class:`DataValue` or
                       :class:`dict` of :class:`unicode` and :class:`DataValue`
                       for Python 2 and :class:`dict` of :class:`str` and
                       :class:`DataValue` for Python 3
        :kwarg values: Dict of field names and field values
        """
        DataValue.__init__(self, data_type)
        self.name = name
        if values is not None and not isinstance(values, dict):
            msg = message_factory.get_message("vapi.data.invalid",
                                              self.type,
                                              type(values).__name__)
            logger.debug(msg)
            raise CoreException(msg)
        self._fields = values if values is not None else {}

    def get_fields(self):
        """
        Returns the map of field names and values present in this
        StructValue.

        :rtype: :class:`dictionary-itemiterator` of :class:`str` and
                :class:`DataValue`
        :return: Fields in this struct value
        """
        return six.iteritems(self._fields)

    def get_field_names(self):
        """
        Returns the list of field names present in this StructValue.
        The ordering of fields is not preserved.

        :rtype: :class:`list` of :class:`str`
        :return: List of field names present in this StructValue
        """
        return list(self._fields.keys())

    def has_field(self, field):
        """
        Returns true if the field is present in the StructValue, false otherwise

        :type  field: :class:`str`
        :param field: Name of the field
        :rtype: :class:`bool`
        :return: Returns true if the field is present in the StructValue,
                 false otherwise
        """
        return field in self._fields

    def get_field(self, field):
        """
        Returns the field value of the field present in the StructValue

        :type  field: :class:`str`
        :param field: Name of the field
        :rtype: :class:`DataValue`
        :return: Returns the field value of the field present in the StructValue
        """
        value = self._fields.get(field)
        if value is None:
            msg = message_factory.get_message(
                "vapi.data.structure.getfield.unknown",
                field)
            logger.debug(msg)
            raise CoreException(msg)
        return value

    def set_field(self, field, value):
        """
        Set the field value for the field name passed in the argument

        :type  field: :class:`str`
        :param field: Name of the field
        :type  field: :class:`str`
        :param field: Name of the field to be set
        :type  value: :class:`DataValue`
        :param value: DataValue to be used for the field
        """
        if value is None:
            msg = message_factory.get_message(
                "vapi.data.structure.setfield.null",
                field)
            logger.debug(msg)
            raise CoreException(msg)

        self._fields[field] = value

    def __eq__(self, other):
        if not isinstance(other, StructValue):
            return False

        if self.name != other.name:
            return False

        if sorted(self.get_field_names()) != sorted(other.get_field_names()):
            return False

        for key, value in six.iteritems(self._fields):
            if value != other.get_field(key):
                return False
        return True

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        return "StructValue(name=%s, values=%s)" % (repr(self.name),
                                                    repr(self._fields))

    def keys(self):
        """
        Returns the list of field names

        :rtype: :class:`list` or :class:`str`
        :return: List of field names
        """
        return six.iterkeys(self._fields)


class ErrorValue(StructValue):
    """
    DataValue class for Errors
    """

    def __init__(self, name=None, values=None):
        """
        Initialize ErrorValue

        :type  name: :class:`str`
        :kwarg name: Name of the ErrorValue
        """
        StructValue.__init__(self, name, Type.ERROR, values)

    def __eq__(self, other):
        if not isinstance(other, ErrorValue):
            return False
        return StructValue.__eq__(self, other)

    def __ne__(self, other):
        return not (self == other)


class SecretValue(PrimitiveDataValue, ComparableValueMixin):
    """
    DataValue class for secret values. Only strings are allowed to be
    secrets.

    :type value: :class:`str`
    :ivar value: String present in SecretValue
    """
    def __init__(self, value=""):
        """
        Initialize StringValue

        :type  value: :class:`str`
        :kwarg value: String value to be initialized
        """
        PrimitiveDataValue.__init__(self, Type.SECRET)
        ComparableValueMixin.__init__(self)
        if not isinstance(value, six.string_types):
            msg = message_factory.get_message("vapi.data.invalid",
                                              self.type,
                                              type(value).__name__)
            raise CoreException(msg)
        self.value = value

    def __repr__(self):
        return 'SecretValue(<secret>)'

    def __str__(self):
        return '<secret>'


class SimpleValueVisitor(VapiVisitor):
    """
    Base no-op implementation of a DataValue visitor
    """
    def __init__(self):
        """
        Initialize SimpleValueVisitor
        """
        VapiVisitor.__init__(self, 'Value')

    def visit_void(self, value):
        """
        Visit a VoidValue

        :type  value: :class:`VoidValue`
        :param value: Data value
        """
        return None

    def visit_integer(self, value):
        """
        Visit a IntegerValue

        :type  value: :class:`IntegerValue`
        :param value: Data value
        """
        return None

    def visit_double(self, value):
        """
        Visit a DoubleValue

        :type  value: :class:`DoubleValue`
        :param value: Data value
        """
        return None

    def visit_string(self, value):
        """
        Visit a StringValue

        :type  value: :class:`StringValue`
        :param value: Data value
        """
        return None

    def visit_boolean(self, value):
        """
        Visit a BooleanValue

        :type  value: :class:`BooleanValue`
        :param value: Data value
        """
        return None

    def visit_blob(self, value):
        """
        Visit a BlobValue

        :type  value: :class:`BlobValue`
        :param value: Data value
        """
        return None

    def visit_list(self, value):
        """
        Visit a ListValue

        :type  value: :class:`ListValue`
        :param value: Data value
        """
        return None

    def visit_optional(self, value):
        """
        Visit a OptionalValue

        :type  value: :class:`OptionalValue`
        :param value: Data value
        """
        return None

    def visit_struct(self, value):
        """
        Visit a StructValue

        :type  value: :class:`StructValue`
        :param value: Data value
        """
        return None

    def visit_error(self, value):
        """
        Visit an ErrorValue

        :type  value: :class:`ErrorValue`
        :param value: Data value
        """
        return None

    def visit_secret(self, value):
        """
        Visit a SecretValue

        :type  value: :class:`SecretValue`
        :param value: Data value
        """
        return None


# vapi type name to vapi type value map
type_map = {
    Type.VOID: VoidValue,
    Type.INTEGER: IntegerValue,
    Type.DOUBLE: DoubleValue,
    Type.STRING: StringValue,
    Type.BOOLEAN: BooleanValue,
    Type.LIST: ListValue,
    Type.STRUCTURE: StructValue,
    Type.ERROR: ErrorValue,
    Type.OPTIONAL: OptionalValue,
    Type.BLOB: BlobValue,
    Type.SECRET: SecretValue,
}


def data_value_factory(data_type, *args):
    """
    Convenience method to create datavalues

    :type  data_type: :class:`str`
    :param data_type: String representation of the data value type
    :param args: The argument list to be passed to the data value constructor
    """
    constructor = type_map.get(data_type)
    return constructor(*args)
