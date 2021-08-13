"""
Data Validator classes
"""

__author__ = 'VMware, Inc.'
__copyright__ = 'Copyright 2015-2017 VMware, Inc.  All rights reserved. -- VMware Confidential'  # pylint: disable=line-too-long

import abc
import itertools
import six

from vmware.vapi.data.value import (
    ListValue, OptionalValue, StringValue, StructValue)
from vmware.vapi.bindings.type import (
    DynamicStructType, ListType, OptionalType, ReferenceType, SetType,
    StructType)
from vmware.vapi.l10n.runtime import message_factory
from vmware.vapi.lib.log import get_vapi_logger

logger = get_vapi_logger(__name__)


@six.add_metaclass(abc.ABCMeta)
class Validator(object):
    """
    vAPI Data object validator class
    This is an abstract class.
    """

    @abc.abstractmethod
    def validate(self, data_value, data_type=None):
        """
        This method validates a data value

        :type data_value :class:`vmware.vapi.data.value.DataValue`
        :param data_value The struct value that needs to be validated
        :type data_type :class:`vmware.vapi.binding.type.BindingType`
        :param data_type The Struct binding type
        :type  ctx: :class:`vmware.vapi.core.ExecutionContext`
        :param ctx: Execution context for this method
        :rtype: :class:`list` of :class:`vmware.vapi.message.Message`
                        or ``None``
        :return List of error messages if validation fails or None
        """
        pass


class UnionValidator(Validator):
    """
    Union Validator class that validates a struct value for union consistency
    """
    def __init__(self, discriminant_name, case_map):
        """
        Initialize the union validator class

        :type discriminant_name :class:`str`
        :param discriminant_name Name of a structure field that represents a
                                 union discriminant
        :type case_map :class:`dict`
        :param case_map Python dict with string value of the discriminant as
                        dictionary key and list of tuple of structure field
                        associated with it and a boolean representing whether
                        it is rqeuired as dictionary value
        """
        self._discriminant_name = discriminant_name
        self._case_map = case_map
        Validator.__init__(self)

    def validate(self, data_value, data_type=None):
        """
        Validates a struct value for union consistency

        :type data_value :class:`vmware.vapi.data.value.DataValue`
        :param data_value The struct value that needs to be validated
        :type data_type :class:`vmware.vapi.binding.type.BindingType`
        :param data_type The Struct binding type
        :type  ctx: :class:`vmware.vapi.core.ExecutionContext`
        :param ctx: Execution context for this method
        :rtype: :class:`list` of :class:`vmware.vapi.message.Message`
                        or ``None``
        :return List of error messages if validation fails or None
        """
        assert(isinstance(data_value, StructValue))
        discriminant = None
        if data_value.has_field(self._discriminant_name):
            # Checking if discriminant is present
            discriminant = data_value.get_field(self._discriminant_name)
            if isinstance(discriminant, OptionalValue):
                discriminant = discriminant.value
        case = None
        if discriminant:
            # Discriminant is present. Find the associated case value
            assert(isinstance(discriminant, StringValue))
            for case_ in six.iterkeys(self._case_map):
                if discriminant == StringValue(case_):
                    case = case_
                    break
        if case:
            # Since case is valid, verify fields requried for this case are
            # present
            for field_name, required in self._case_map[case]:
                missing = False
                if data_value.has_field(field_name):
                    field_value = field = data_value.get_field(field_name)
                    if isinstance(field, OptionalValue):
                        field_value = field.value
                    if required and field_value is None:
                        #Validation failed
                        missing = True
                elif required:
                    #Validation failed
                    missing = True
                if missing:
                    msg = message_factory.get_message(
                        'vapi.data.structure.union.missing',
                        data_value.name, field_name)
                    logger.debug(msg)
                    return [msg]
        all_case_fields = set(itertools.chain(*six.itervalues(self._case_map)))
        allowed_case_field_names = []
        if case:
            allowed_case_field_names = [f for f, _ in self._case_map[case]]
        prohibited_case_field_names = [f for f, _ in all_case_fields
                                       if f not in allowed_case_field_names]

        # Verify that remaining fields are not present
        for field_name in prohibited_case_field_names:
            if data_value.has_field(field_name):
                field_value = field = data_value.get_field(field_name)
                if isinstance(field, OptionalValue):
                    field_value = field.value
                if field_value is not None:
                    #Validation failed
                    msg = message_factory.get_message(
                        'vapi.data.structure.union.extra',
                        data_value.name, field_name)
                    logger.debug(msg)
                    return [msg]


class HasFieldsOfValidator(Validator):
    """
    HasFieldsOfValidator validator class that validates the data_value has
    required fields of the class specified
    """

    def __init__(self):
        Validator.__init__(self)

    def validate(self, data_value, data_type=None):
        """
        Validates whether a StructValue satisfies the HasFieldsOf constraint

        :type data_value :class:`vmware.vapi.data.value.DataValue`
        :param data_value The struct value that needs to be validated
        :type data_type :class:`vmware.vapi.binding.type.BindingType`
        :param data_type The Struct binding type
        :type  ctx: :class:`vmware.vapi.core.ExecutionContext`
        :param ctx: Execution context for this method
        :rtype: :class:`list` of :class:`vmware.vapi.message.Message`
                        or ``None``
        :return List of error messages if validation fails or None
        """
        assert(data_type is not None)
        return self._validate_int(data_value, data_type)

    @classmethod
    def _validate_int(cls, data_value, data_type):  # pylint: disable=R0911
        """
        Validates a data value recursively. This is an internal method.

        :type data_value :class:`vmware.vapi.data.value.DataValue`
        :param data_value The struct value that needs to be validated
        :type data_type :class:`vmware.vapi.binding.type.BindingType`
        :param data_type The Struct binding type
        :rtype: :class:`list` of :class:`vmware.vapi.message.Message`
                        or ``None``
        :return List of error messages if validation fails or None
        """
        if isinstance(data_type, DynamicStructType):
            if data_type.has_fields_of_type:
                for type_ in data_type.has_fields_of_type:
                    assert(isinstance(type_, ReferenceType))
                    resolved_type = type_.resolved_type
                    for field_name in resolved_type.get_field_names():
                        field_type = resolved_type.get_field(field_name)
                        if not data_value.has_field(field_name):
                            if isinstance(field_type, OptionalType):
                                continue
                            msg = message_factory.get_message(
                                'vapi.data.structure.dynamic.missing',
                                field_name, resolved_type.name)
                            logger.debug(msg)
                            return [msg]
                        field_value = data_value.get_field(field_name)
                        if type(field_type) not in [
                                ReferenceType, ListType, SetType, OptionalType,
                                StructType, DynamicStructType]:
                            # Data value validation for primitive types
                            msg_list = field_type.definition.validate(
                                field_value)
                            if msg_list:
                                return msg_list
                        else:
                            # Custom Validation for other types
                            msg_list = cls._validate_int(field_value,
                                                         field_type)
                            if msg_list:
                                return msg_list
        elif isinstance(data_type, ReferenceType):
            return cls._validate_int(data_value, data_type.resolved_type)
        elif isinstance(data_type, ListType) or isinstance(data_type, SetType):
            assert(isinstance(data_value, ListValue))
            for val in data_value:
                msg_list = cls._validate_int(val, data_type.element_type)
                if msg_list:
                    return msg_list
        elif isinstance(data_type, OptionalType):
            if isinstance(data_value, OptionalValue):
                data_value = data_value.value
            if data_value is not None:
                msg_list = cls._validate_int(data_value, data_type.element_type)
                if msg_list:
                    return msg_list
        elif isinstance(data_type, StructType):
            for field_name in data_type.get_field_names():
                field_type = data_type.get_field(field_name)
                if data_value.has_field(field_name):
                    field_value = data_value.get_field(field_name)
                    msg_list = cls._validate_int(field_value, field_type)
                    if msg_list:
                        return msg_list
                elif not isinstance(field_type, OptionalType):
                    msg = message_factory.get_message(
                        'vapi.data.structure.field.missing',
                        field_type, field_name)
                    logger.debug(msg)
                    return [msg]
